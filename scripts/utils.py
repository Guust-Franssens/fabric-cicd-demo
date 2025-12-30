import json
import os
import re
import subprocess
from pathlib import Path
from string import Template

from config import DEPLOY_CONFIG


def run_fab_command(command, capture_output: bool = False, silently_continue: bool = False, timeout: int = 300):
    """Run fabric CLI command with timeout protection (default 5 minutes)."""
    try:
        result = subprocess.run(["fab", "-c", command], capture_output=capture_output, text=True, timeout=timeout)
        if not (silently_continue) and (result.returncode > 0 or result.stderr):
            msg = (
                f"Error running fab command: {command}\n"
                f"exit_code: '{result.returncode}'; stderr: '{result.stderr}'; stdout: '{result.stdout}'"
            )
            raise Exception(msg)
        if capture_output:
            output = result.stdout.strip()
            return output
    except subprocess.TimeoutExpired:
        raise Exception(f"Command timed out after {timeout} seconds: {command}")


def create_connection(connection_name: str = None, parameters: dict = None, upns: list = None):
    """
    Creates a connection with the specified name, parameters, and UPNs.
    Args:
        connection_name (str, optional): The name of the connection to create. Defaults to None.
        parameters (dict, optional): A dictionary of parameters to include in the connection. Defaults to None.
        upns (list, optional): A list of UPNs to add to the connection with admin rights. Defaults to None.
    Returns:
        str: The ID of the created connection.
    """
    if parameters:
        param_str = ",".join(f"{key}={value}" for key, value in parameters.items())
        param_str = f"-P {param_str}"
    else:
        param_str = ""

    run_fab_command(
        f"create .connections/{connection_name}.Connection {param_str}",
        silently_continue=True,
    )

    connection_id = run_fab_command(f"get .connections/{connection_name}.Connection -q id", capture_output=True)

    if upns is not None:
        upns = [x for x in upns if x.strip()]
        if len(upns) > 0:
            print(f"Adding UPNs to item {connection_name}")
            for upn in upns:
                run_fab_command(f"acl set -f .connections/{connection_name}.Connection -I {upn} -R admin")

    return connection_id


def exists(item_path: str) -> bool:
    """
    Checks if an item exists at the specified path.
    Args:
        item_path (str): The path of the item to check.

    Returns:
        bool: True if the item exists, False otherwise.
    """
    result = run_fab_command(f"exists {item_path} --output_format json", capture_output=True)
    message = json.loads(result)["result"]["message"]
    if isinstance(message, bool):
        return message
    return str(message).strip().lower() == "true"


def _render_template(template: str, values: dict[str, object], *, strict: bool = True) -> str:
    """Render a $placeholder template using string.Template.

    Note: values are escaped for safe use in re.sub replacement strings.
    """
    template_values = {k: str(v).replace("\\", r"\\") for k, v in values.items()}
    tpl = Template(template)
    if strict:
        try:
            return tpl.substitute(template_values)
        except KeyError as e:
            missing = e.args[0]
            raise KeyError(f"Missing template value for '${missing}'") from e
    return tpl.safe_substitute(template_values)


def deploy_lakehouse(workspace_name: str, lakehouse_path: str | Path) -> str:
    """
    Deploys a lakehouse to a specified workspace using fab create (not fab import).
    """
    if not str(lakehouse_path).lower().endswith(".lakehouse"):
        raise ValueError("lakehouse_path must have a .lakehouse extension")

    path = f"/{workspace_name}.workspace/{lakehouse_path.name}"
    result = run_fab_command(f"exists {path} --output_format json", capture_output=True)
    exists = json.loads(result)["result"]["message"]
    if exists == "false" or (isinstance(exists, bool) and not exists):
        run_fab_command(f"create {path} -P enableSchemas=true")

    result = run_fab_command(f"get {path} -q id --output_format json", capture_output=True)
    lakehouse_id = json.loads(result)["result"]["data"][0]
    return lakehouse_id


def get_sql_endpoint(workspace_name: str, lakehouse_path: str | Path) -> str:
    """
    Retrieves the SQL endpoint associated with a given lakehouse ID.
    Args:
        lakehouse_id (str): The ID of the lakehouse.
    Returns:
        str: The SQL endpoint of the lakehouse.
    """
    if not str(lakehouse_path).lower().endswith(".lakehouse"):
        raise ValueError("lakehouse_path must have a .lakehouse extension")

    path = f"/{workspace_name}.workspace/{lakehouse_path.name}"
    result = run_fab_command(
        f"get {path} -q properties.sqlEndpointProperties.connectionString --output_format json",
        capture_output=True,
    )
    sql_endpoint = json.loads(result)["result"]["data"][0]
    return sql_endpoint


def deploy_item(
    item_path: Path,
    workspace_name,
    find_and_replace: dict[str, object] | None = None,
    what_if: bool = False,
) -> str | None:
    """
    Deploys an item to a specified workspace.
    Args:
        item_path (str): The source path of the item to be deployed.
        workspace_name (str): The name of the workspace where the item will be deployed.
        find_and_replace (dict, optional): A dictionary where keys are tuples containing a file filter regex and a find regex,
                                           and values are the replacement strings. This will be used to perform find and replace
                                           operations on the files in the staging path.
        what_if (bool, optional): If True, the deployment will be simulated but not actually performed. Defaults to False.
    Returns:
        str: The ID of the deployed item if `what_if` is False. Otherwise, returns None.
    """
    # Call function that provides flexibility to change something in the staging files
    item_name = item_path.stem
    item_type = item_path.suffix.lstrip(".")

    # cli currently does not yet support deploying lakehouses via item definition (fab import)
    # should come soon as lakehouse item definition is recently supported
    # https://learn.microsoft.com/en-us/rest/api/fabric/lakehouse/items/get-lakehouse-definition
    if item_type.lower() == "lakehouse":
        return deploy_lakehouse(workspace_name, item_path)

    platform_file = item_path / ".platform"
    if platform_file.exists():
        with open(platform_file, "r") as file:
            platform_data = json.load(file)

        if item_name is None:
            item_name = platform_data["metadata"]["displayName"]

        if item_type is None:
            item_type = platform_data["metadata"]["type"]

    # Loop through all files and apply the DEPLOY_CONFIG replacements.
    # `find_and_replace` is a simple mapping of placeholder -> value, e.g.
    # {"workspace_id": "...", "lakehouse_id": "...", "sql_endpoint": "..."}
    if find_and_replace is None:
        find_and_replace = {}

    if item_type in DEPLOY_CONFIG:
        value = DEPLOY_CONFIG[item_type]
        for file_path in item_path.rglob("*"):
            if file_path.name not in value:
                continue

            with open(file_path, "r") as file:
                text = file.read()

            to_replace_list = value[file_path.name]
            for replace in to_replace_list:
                pattern = replace["pattern"]
                replacement_template = replace["replacement"]
                replacement = _render_template(replacement_template, find_and_replace, strict=True)

                text, _count_subs = re.subn(pattern, replacement, text)

            with open(file_path, "w") as file:
                file.write(text)

    command = f"import -f /{workspace_name}.workspace/{item_name}.{item_type} -i {item_path}"
    if what_if:
        print(f"fab {command}")
    else:
        run_fab_command(command + f" {'--format .py' if item_type == 'Notebook' else ''}")
        # Return id after deployment
        item_id = run_fab_command(
            f"get /{workspace_name}.workspace/{item_name}.{item_type} -q id",
            capture_output=True,
        )

        return item_id
