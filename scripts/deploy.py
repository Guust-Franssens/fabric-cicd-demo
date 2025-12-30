import argparse
import glob
import shutil
import tempfile
from pathlib import Path

from utils import create_connection, deploy_item, get_sql_endpoint, run_fab_command

DEPLOY_ORDER = ["lakehouse", "semanticmodel", "report", "notebook", "datapipeline"]
PROJECT_ROOT = Path(__file__).parent.parent
ITEMS_FOLDER = PROJECT_ROOT / "src"
CONNECTION_NAME = "conn-cicd-demo"
CONNECTION_SOURCE_URL = "https://raw.githubusercontent.com/pbi-tools/sales-sample/refs/heads/data/RAW-Sales.csv"
CONNECTION_PARAMETERS = {
    "connectionDetails.type": "HttpServer",
    "connectionDetails.parameters.url": CONNECTION_SOURCE_URL,
    "credentialDetails.type": "Anonymous",
}


def main(workspace_name: str):
    # Remove .workspace or .Workspace suffix if present
    workspace_name = workspace_name.removesuffix(".workspace").removesuffix(".Workspace")
    workspace_id = run_fab_command(f"get /{workspace_name}.Workspace -q id", capture_output=True)

    # create connection to use in data pipeline
    connection_id = create_connection(connection_name=CONNECTION_NAME, parameters=CONNECTION_PARAMETERS)

    # copy items to temporary folder
    with tempfile.TemporaryDirectory(prefix=f"{workspace_name}_", suffix="_deployment") as temp_base:
        temp_items_folder = Path(temp_base) / "items"
        temp_dir = shutil.copytree(ITEMS_FOLDER, temp_items_folder, ignore=shutil.ignore_patterns("*.abf"))
        items = list(Path(temp_dir).glob("*"))

        variables = {"workspace_id": workspace_id, "connection_id": connection_id}
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--workspace-name", type=str, required=True, help="The name of the workspace to deploy to.")
    args = parser.parse_args()
    main(args.workspace_name)
