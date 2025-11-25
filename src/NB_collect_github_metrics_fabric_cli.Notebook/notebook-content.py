# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.11"
# META   }
# META }

# MARKDOWN ********************

# # GitHub Metrics Collection for microsoft/fabric-cli
# This notebook collects various metrics from the microsoft/fabric-cli repository for Power BI reporting

# CELL ********************

import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from deltalake import write_deltalake

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

# Configuration
REPO_OWNER = "microsoft"
REPO_NAME = "fabric-cli"
BASE_URL = "https://api.github.com"

# Optional: Add your GitHub token for higher rate limits
# Get token from: https://github.com/settings/tokens
GITHUB_TOKEN = ""  # Leave empty if you don't have a token

# Setup headers
headers = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    headers["Authorization"] = f"token {GITHUB_TOKEN}"

print(f"Collecting metrics for {REPO_OWNER}/{REPO_NAME}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************


def make_github_request(url):
    """Make a request to GitHub API with error handling"""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to {url}: {e}")
        return None


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 1. Basic Repository Metrics

# CELL ********************

# Get basic repository information
repo_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}"
repo_data = make_github_request(repo_url)

if repo_data:
    basic_metrics = {
        "metric": [
            "Stars",
            "Forks",
            "Open Issues",
            "Watchers",
            "Size (KB)",
            "Created Date",
            "Last Updated",
            "Default Branch",
            "Language",
            "Has Wiki",
            "Has Issues",
            "Has Projects",
            "Has Downloads",
        ],
        "value": [
            repo_data["stargazers_count"],
            repo_data["forks_count"],
            repo_data["open_issues_count"],
            repo_data["watchers_count"],
            repo_data["size"],
            repo_data["created_at"],
            repo_data["updated_at"],
            repo_data["default_branch"],
            repo_data["language"],
            repo_data["has_wiki"],
            repo_data["has_issues"],
            repo_data["has_projects"],
            repo_data["has_downloads"],
        ],
    }

    df_basic_metrics = pd.DataFrame(basic_metrics)
    print("Basic Repository Metrics:")
    print(df_basic_metrics.to_string(index=False))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 2. Contributors Analysis

# CELL ********************

# Get contributors
contributors_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/contributors"
contributors = []
page = 1

while True:
    response = requests.get(f"{contributors_url}?page={page}&per_page=100", headers=headers)
    if response.status_code != 200:
        break

    page_data = response.json()
    if not page_data:
        break

    contributors.extend(page_data)
    page += 1

    # Avoid hitting rate limits
    time.sleep(0.5)

if contributors:
    df_contributors = pd.DataFrame(
        [
            {
                "contributor": c["login"],
                "contributions": c["contributions"],
                "avatar_url": c["avatar_url"],
                "profile_url": c["html_url"],
            }
            for c in contributors
        ]
    )

    print(f"\nTotal Contributors: {len(df_contributors)}")
    print("Top 10 Contributors:")
    print(df_contributors.head(10)[["contributor", "contributions"]].to_string(index=False))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 3. Branches Information

# CELL ********************

# Get branches
branches_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/branches"
branches = []
page = 1

while True:
    response = requests.get(f"{branches_url}?page={page}&per_page=100", headers=headers)
    if response.status_code != 200:
        break

    page_data = response.json()
    if not page_data:
        break

    branches.extend(page_data)
    page += 1
    time.sleep(0.5)

if branches:
    df_branches = pd.DataFrame(
        [
            {
                "branch_name": b["name"],
                "protected": b.get("protected", False),
                "commit_sha": b["commit"]["sha"][:7],  # Short SHA
            }
            for b in branches
        ]
    )

    branch_metrics = {
        "metric": ["Total Branches", "Protected Branches", "Unprotected Branches"],
        "value": [
            len(df_branches),
            df_branches["protected"].sum(),
            (~df_branches["protected"]).sum(),
        ],
    }

    df_branch_metrics = pd.DataFrame(branch_metrics)
    print("\nBranch Metrics:")
    print(df_branch_metrics.to_string(index=False))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 4. Recent Commits Analysis

# CELL ********************

# Get recent commits
commits_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/commits"
commits = make_github_request(f"{commits_url}?per_page=100")

if commits:
    df_commits = pd.DataFrame(
        [
            {
                "sha": c["sha"][:7],
                "author": c["commit"]["author"]["name"] if c["commit"]["author"] else "Unknown",
                "date": c["commit"]["author"]["date"] if c["commit"]["author"] else None,
                "message": c["commit"]["message"][:100] + "..."
                if len(c["commit"]["message"]) > 100
                else c["commit"]["message"],
            }
            for c in commits
        ]
    )

    df_commits["date"] = pd.to_datetime(df_commits["date"])

    # Commits by day of week
    df_commits["day_of_week"] = df_commits["date"].dt.day_name()
    commits_by_day = df_commits["day_of_week"].value_counts()

    # Commits in last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_commits = df_commits[df_commits["date"] > thirty_days_ago]

    print("\nCommit Activity (Last 100 commits):")
    print(f"Total commits analyzed: {len(df_commits)}")
    print(f"Commits in last 30 days: {len(recent_commits)}")
    print(f"\nMost active day: {commits_by_day.index[0]} ({commits_by_day.iloc[0]} commits)")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 5. Pull Requests Analysis

# CELL ********************

# Get pull requests
prs_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/pulls"

# Get open PRs
open_prs = make_github_request(f"{prs_url}?state=open&per_page=100")
# Get closed PRs
closed_prs = make_github_request(f"{prs_url}?state=closed&per_page=100")

pr_metrics = {
    "metric": ["Open PRs", "Recently Closed PRs (last 100)"],
    "value": [len(open_prs) if open_prs else 0, len(closed_prs) if closed_prs else 0],
}

df_pr_metrics = pd.DataFrame(pr_metrics)
print("\nPull Request Metrics:")
print(df_pr_metrics.to_string(index=False))

if open_prs:
    df_open_prs = pd.DataFrame(
        [
            {
                "number": pr["number"],
                "title": pr["title"][:50] + "..." if len(pr["title"]) > 50 else pr["title"],
                "author": pr["user"]["login"],
                "created_at": pr["created_at"],
                "draft": pr.get("draft", False),
            }
            for pr in open_prs[:10]  # Show first 10
        ]
    )

    print("\nOpen Pull Requests (First 10):")
    print(df_open_prs[["number", "title", "author"]].to_string(index=False))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 6. Issues Analysis

# CELL ********************

# Get issues (excluding PRs)
issues_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues"

# Get open issues
open_issues = make_github_request(f"{issues_url}?state=open&per_page=100")
# Get closed issues
closed_issues = make_github_request(f"{issues_url}?state=closed&per_page=100")

# Filter out pull requests (they appear in issues endpoint too)
if open_issues:
    open_issues = [i for i in open_issues if "pull_request" not in i]
if closed_issues:
    closed_issues = [i for i in closed_issues if "pull_request" not in i]

issue_metrics = {
    "metric": ["Open Issues", "Recently Closed Issues (last 100)"],
    "value": [
        len(open_issues) if open_issues else 0,
        len(closed_issues) if closed_issues else 0,
    ],
}

df_issue_metrics = pd.DataFrame(issue_metrics)
print("\nIssue Metrics:")
print(df_issue_metrics.to_string(index=False))

# Analyze labels in open issues
if open_issues:
    all_labels = []
    for issue in open_issues:
        all_labels.extend([label["name"] for label in issue["labels"]])

    if all_labels:
        label_counts = pd.Series(all_labels).value_counts().head(10)
        print("\nTop 10 Labels in Open Issues:")
        for label, count in label_counts.items():
            print(f"  {label}: {count}")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 7. Release Information

# CELL ********************

# Get releases
releases_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/releases"
releases = make_github_request(f"{releases_url}?per_page=10")

if releases:
    df_releases = pd.DataFrame(
        [
            {
                "name": r["name"] or r["tag_name"],
                "tag": r["tag_name"],
                "published_at": r["published_at"],
                "prerelease": r["prerelease"],
                "draft": r["draft"],
            }
            for r in releases
        ]
    )

    df_releases["published_at"] = pd.to_datetime(df_releases["published_at"])

    # Calculate days since last release
    if len(df_releases) > 0:
        days_since_last_release = (datetime.now() - df_releases["published_at"].iloc[0].replace(tzinfo=None)).days

        print("\nRelease Metrics:")
        print(f"Total Releases: {len(releases)}")
        print(f"Latest Release: {df_releases['name'].iloc[0]} ({df_releases['tag'].iloc[0]})")
        print(f"Days Since Last Release: {days_since_last_release}")
        print("\nRecent Releases (Last 5):")
        print(df_releases[["name", "tag", "published_at"]].head(5).to_string(index=False))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 8. Language Statistics

# CELL ********************

# Get language statistics
languages_url = f"{BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/languages"
languages = make_github_request(languages_url)

if languages:
    total_bytes = sum(languages.values())
    df_languages = pd.DataFrame(
        [
            {
                "language": lang,
                "bytes": bytes_count,
                "percentage": round((bytes_count / total_bytes) * 100, 2),
            }
            for lang, bytes_count in languages.items()
        ]
    ).sort_values("bytes", ascending=False)

    print("\nLanguage Distribution:")
    print(df_languages.to_string(index=False))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## 9. Export Data for Power BI

# CELL ********************

# Compile all metrics into exportable dataframes
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create a summary metrics dataframe
summary_metrics = {
    "metric_category": [],
    "metric_name": [],
    "metric_value": [],
    "timestamp": [],
}

# Add all metrics
if repo_data:
    summary_metrics["metric_category"].extend(["Repository"] * 4)
    summary_metrics["metric_name"].extend(["Stars", "Forks", "Open Issues", "Watchers"])
    summary_metrics["metric_value"].extend(
        [
            repo_data["stargazers_count"],
            repo_data["forks_count"],
            repo_data["open_issues_count"],
            repo_data["watchers_count"],
        ]
    )
    summary_metrics["timestamp"].extend([datetime.now()] * 4)

df_summary = pd.DataFrame(summary_metrics)

print("\n" + "=" * 50)
print("DATA EXPORT SUMMARY")
print("=" * 50)
print("\nDataframes created for Power BI:")
print("1. df_summary - Overall metrics summary")
print("2. df_contributors - Contributor details")
print("3. df_branches - Branch information")
print("4. df_commits - Recent commit history")
print("5. df_languages - Language distribution")
if "df_releases" in locals():
    print("6. df_releases - Release history")

print("\nThese dataframes can now be used directly in Power BI visualizations!")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

if lakehouses := notebookutils.lakehouse.list():
    abfspath = lakehouses[0].properties["abfsPath"]
    storage_options = {
        "bearer_token": notebookutils.credentials.getToken("storage"),
        "use_fabric_endpoint": "true",
    }
    kwargs = dict(
        mode="overwrite",
        schema_mode="merge",
        engine="rust",
        storage_options=storage_options,
    )
    write_deltalake(f"{abfspath}/Tables/dbo/summary", df_summary, **kwargs)
    write_deltalake(f"{abfspath}/Tables/dbo/contributors", df_contributors, **kwargs)
    write_deltalake(f"{abfspath}/Tables/dbo/branches", df_branches, **kwargs)
    write_deltalake(f"{abfspath}/Tables/dbo/commits", df_commits, **kwargs)
    write_deltalake(f"{abfspath}/Tables/dbo/languages", df_languages, **kwargs)
    if "df_releases" in locals():
        write_deltalake(f"{abfspath}/Tables/dbo/releases", df_releases, **kwargs)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# MARKDOWN ********************

# ## Power BI Integration Instructions
#
# ### Using this notebook in Microsoft Fabric:
#
# 1. **In Fabric Workspace:**
#    - Create a new Notebook
#    - Copy this code into the notebook
#    - Run all cells to collect the data
#
# 2. **Creating Power BI Report:**
#    - The dataframes created in this notebook can be directly accessed in Power BI
#    - Create a new Power BI report in the same workspace
#    - Use "Get Data" → "OneLake data hub" to access the notebook data
#
# 3. **Suggested Visualizations:**
#    - **KPI Cards**: Stars, Forks, Open Issues, Contributors
#    - **Line Chart**: Commit activity over time
#    - **Bar Chart**: Top contributors, Language distribution
#    - **Table**: Recent releases, Open PRs
#    - **Pie Chart**: Issue labels distribution
#    - **Gauge**: Days since last release
#
# 4. **Refresh Strategy:**
#    - Schedule this notebook to run daily/weekly
#    - Use Fabric Data Pipeline to automate the refresh
#    - Power BI will automatically reflect updated data
