"""
Deployment configuration for Fabric items.

This file contains find-and-replace patterns for deploying various Fabric items.
Use $variable_name syntax for placeholders that will be substituted at runtime.
"""

import json

DEPLOY_CONFIG = {
    "DataPipeline": {
        "pipeline-content.json": [
            {
                # Replace workspace ID in the pipeline configuration
                "pattern": r'("workspaceId"\s*:\s*)".*"',
                "replacement": r'\1"$workspace_id"',
            },
            {
                # Replace artifact ID (lakehouse ID) in the pipeline configuration
                "pattern": r'("artifactId"\s*:\s*)".*"',
                "replacement": r'\1"$lakehouse_id"',
            },
            {
                # Replace connection ID in the pipeline configuration
                "pattern": r'("connection"\s*:\s*)".*"',
                "replacement": r'\1"$connection_id"',
            },
        ]
    },
    "Notebook": {
        "notebook-content.py": [
            {
                # Set the default lakehouse ID for the notebook
                "pattern": r'("default_lakehouse"\s*:\s*)".*"',
                "replacement": r'\1"$lakehouse_id"',
            },
            {
                # Set the default lakehouse name for the notebook
                "pattern": r'("default_lakehouse_name"\s*:\s*)".*"',
                "replacement": r'\1"$lakehouse_name"',
            },
            {
                # Set the default lakehouse workspace ID for the notebook
                "pattern": r'("default_lakehouse_workspace_id"\s*:\s*)".*"',
                "replacement": r'\1"$workspace_id"',
            },
            {
                # Replace the known lakehouses array with the current lakehouse
                "pattern": r'(#\s*META\s+"known_lakehouses"\s*:\s*)\[[\s\S]*?\]',
                "replacement": r"""\1[
# META         {
# META           "id": "$lakehouse_id"
# META         }
# META       ]""",
            },
        ]
    },
    "SemanticModel": {
        "expressions.tmdl": [
            {
                # Replace the SQL endpoint server connection in the semantic model
                "pattern": r'(expression\s+Server\s*=\s*)".*?"',
                "replacement": r'\1"$sql_endpoint"',
            }
        ]
    },
    "Report": {
        "definition.pbir": [
            {
                # Replace the entire dataset reference with the semantic model ID
                "pattern": r"\{[\s\S]*\}",
                "replacement": json.dumps(
                    {
                        "version": "4.0",
                        "datasetReference": {
                            "byConnection": {
                                "connectionString": None,
                                "pbiServiceModelId": None,
                                "pbiModelVirtualServerName": "sobe_wowvirtualserver",
                                "pbiModelDatabaseName": "$semanticmodel_id",
                                "name": "EntityDataSource",
                                "connectionType": "pbiServiceXmlaStyleLive",
                            }
                        },
                    }
                ),
            }
        ]
    },
}
