import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from utils import bind_semantic_model_connection, create_connection, deploy_item, get_sql_endpoint, run_fab_command

DEPLOY_ORDER = ["lakehouse", "semanticmodel", "report", "notebook", "datapipeline"]
PROJECT_ROOT = Path(__file__).parent.parent
ITEMS_FOLDER = PROJECT_ROOT / "src"
PL_CONNECTION_NAME = "conn-cicd-demo"
PL_CONNECTION_SOURCE_URL = "https://raw.githubusercontent.com/pbi-tools/sales-sample/refs/heads/data/RAW-Sales.csv"
PL_CONN_PARAMS = {
    "connectionDetails.type": "HttpServer",
    "connectionDetails.parameters.url": PL_CONNECTION_SOURCE_URL,
    "credentialDetails.type": "Anonymous",
}
DATABASE = "lh_store_raw"
SM_CONN_PARAMS = {
    "connectivityType": "ShareableCloud",
    "connectionDetails.creationMethod": "SQL",
    "connectionDetails.type": "SQL",
    "connectionDetails.parameters.database": DATABASE,
    "privacyLevel": "Organizational",
    "credentialDetails.skipTestConnection": "False",
    "credentialDetails.type": "WorkspaceIdentity",
}
ADMIN_UPNS = os.getenv("SECGROUP_ADMINS_ID", "").split(",") if os.getenv("SECGROUP_ADMINS_ID") else None


def main(workspace_name: str):
    # Remove .workspace or .Workspace suffix if present
    workspace_name = workspace_name.removesuffix(".workspace").removesuffix(".Workspace")
    workspace_id = run_fab_command(f"get /{workspace_name}.Workspace -q id", capture_output=True)

    # create connection to use in data pipeline
    pl_connection_id = create_connection(connection_name=PL_CONNECTION_NAME, parameters=PL_CONN_PARAMS, upns=ADMIN_UPNS)

    # copy items to temporary folder
    with tempfile.TemporaryDirectory(prefix=f"{workspace_name}_", suffix="_deployment") as temp_base:
        temp_items_folder = Path(temp_base) / "items"
        temp_dir = shutil.copytree(ITEMS_FOLDER, temp_items_folder, ignore=shutil.ignore_patterns("*.abf"))
        items = list(Path(temp_dir).glob("*"))

        variables = {"workspace_id": workspace_id, "connection_id": pl_connection_id}
        for item_type in DEPLOY_ORDER:
            items_ = [item for item in items if item.suffix.lower() == f".{item_type}"]
            for item in items_:
                item_id = deploy_item(item, workspace_name, find_and_replace=variables)
                if item_type == "lakehouse":
                    variables["lakehouse_id"] = item_id
                    variables["lakehouse_name"] = item.stem
                    variables["sql_endpoint"] = get_sql_endpoint(workspace_name, item)

                if item_type == "semanticmodel":
                    variables["semanticmodel_id"] = item_id

        # create connections to use in semantic model
        SM_CONN_PARAMS["connectionDetails.parameters.server"] = variables["sql_endpoint"]
        conn_name = f"conn-cicd-{variables['sql_endpoint']}"
        sm_connection_id = create_connection(connection_name=conn_name, parameters=SM_CONN_PARAMS, upns=ADMIN_UPNS)

        # bind the semantic model to the lakehouse with the created connection
        if "semanticmodel_id" in variables:
            result = bind_semantic_model_connection(
                workspace_id=workspace_id,
                semantic_model_id=variables["semanticmodel_id"],
                connection_id=sm_connection_id,
                sql_endpoint=variables["sql_endpoint"],
                database=DATABASE,
            )
            if isinstance(result, dict) and result["status_code"] < 300:
                print("Semantic model connection bound successfully.")
            else:
                print(f"Failed to bind semantic model connection: {result}")

        # run all data pipelines
        command = f'ls "/{workspace_name}.workspace" -q "[?contains(name, \'.DataPipeline\')]" --output_format json'
        result = json.loads(run_fab_command(command, capture_output=True))
        for dp in result["result"]["data"]:
            run_fab_command(f'job run "/{workspace_name}.workspace/{dp["name"]}"')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--workspace-name", type=str, required=True, help="The name of the workspace to deploy to.")
    args = parser.parse_args()
    main(args.workspace_name)
