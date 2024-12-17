# JIRA to GitHub Issue Migration Tool

This tool is a Python application developed to automatically migrate work items (issues) from JIRA-exported XML files to GitHub.

## 🎯 Purpose

This application performs the following core functions:

- Reading and processing XML files exported from JIRA
- Automatically distributing issues to Frontend and Backend repositories
- GitHub Projects integration
- Preventing duplicates by checking existing issues
- Maintaining issue statuses

## 🔍 Key Features

### XML File Processing
- Reads issues from XML file
- Filters out issues with "Cancelled" status
- Sorts by title
- Provides pagination support

### GitHub Integration
- Automatic issue assignment to Frontend and Backend repositories
- GitHub Projects integration
- Preservation of issue statuses
- Existing issue verification

### Smart Labeling
- Repository selection based on Frontend/Backend labels
- Preservation of JIRA IDs
- Transfer of priority and status information

## 🛠 Technical Details

### Used Technologies
- GitHub REST API v3
  - Issue creation and management
  - Repository operations
  - Label management
- GitHub GraphQL API v4
  - Project management
  - Complex queries for issue status updates
- Python Libraries
  - `requests`: HTTP client for REST API and GraphQL calls
  - `github`: GitHub REST API client
  - `xml.etree.ElementTree`: XML parsing
  - `re`: Regular expressions for text processing

### Repository Determination Logic
- Issues with "Frontend" label go to Frontend repository
- Issues with "Backend" label go to Backend repository
- Defaults to Backend repository

### Issue Processing Flow
1. Issues are read from XML file
2. For each issue:
   - Title is cleaned (JIRA ID removed)
   - Description is formatted
   - Labels are organized
   - Status is verified
   - Created in GitHub
   - Added to project
   - Status updated

### Error Handling
- Error checking for each operation
- Detailed logging
- Time delays for rate limiting

## 📋 Usage

1. Set up your GitHub token
2. Update repository information
3. Prepare the JIRA-exported XML file
   - Export issues from JIRA as XML format
   - Save as `jira-issues.xml` in project root directory
   - File must contain standard JIRA XML structure with issues
4. Run the script:

```bash
python gh.py
```

## ⚙️ Configuration

Basic settings are located at the beginning of `gh.py`:

```python
GITHUB_TOKEN = "your-token-here"
REPO_FE = "organization/frontend-repo"
REPO_BE = "organization/backend-repo"
```

### Required GitHub Token Permissions

#### Organization Permissions
- Read and Write access to organization projects

#### Repository Permissions
- Read access to metadata
- Read and Write access to issues

> Note: These permissions are required for the script to create issues and manage project boards. Make sure your token has all these permissions before running the script.

## 🔄 Process Flow

1. Existing GitHub issues are checked
2. XML file is parsed
3. For each issue:
   - Repository is determined
   - Duplicate check is performed
   - Created in GitHub
   - Added to project
   - Status updated

## ⚠️ Important Notes

- Ensure GitHub token is correctly set before running the script
- Wait times are added between operations due to rate limiting
- Pagination is recommended for large XML files
- The `jira-issues.xml` file must be present in the project root directory
- XML file should follow JIRA's standard export format structure
