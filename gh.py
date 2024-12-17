import xml.etree.ElementTree as ElTree
from github import Github
import time
import requests
import re

# GitHub token'ınızı buraya girin
GITHUB_TOKEN = "{GITHUB_TOKEN}"

# GitHub repo bilgilerinizi buraya girin
# REPO_TEST = "datarul/test-issue"
REPO_FE = "{ORGANIZATION/FRONTEND-REPO}"
REPO_BE = "{ORGANIZATION/BACKEND-REPO}"

# Global değişkenler olarak issue title'larını tutacak setler
FE_ISSUE_TITLES = set()
BE_ISSUE_TITLES = set()

# Renk kodlarını en üstte tanımlayalım
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


# Repo belirleme fonksiyonu
def determine_repo(labels):
    if "Frontend" in labels:
        return REPO_FE
    elif "Backend" in labels:
        return REPO_BE
    return REPO_BE  # varsayılan repo


def parse_jira_xml(file_path, skip=0, take=None):
    tree = ElTree.parse(file_path)
    root = tree.getroot()
    issues = []

    # Tüm issue'ları al
    all_items = root.findall(".//item")

    # Cancelled olmayan issue'ları filtrele
    valid_items = [
        item for item in all_items if item.find("status").text.lower() != "cancelled"
    ]

    # Title'a göre sırala
    valid_items.sort(key=lambda x: x.find("title").text.lower())

    # Sayfalama uygula
    paginated_items = valid_items[skip:]
    if take is not None:
        paginated_items = paginated_items[:take]

    for item in paginated_items:
        status = item.find("status").text
        full_title = item.find("title").text
        description = item.find("description").text or "No description provided."

        # [DG-XX] pattern'ini bul ve çıkar
        pattern = r"\[DG-\d+\]"
        match = re.search(pattern, full_title)
        jira_id = match.group(0) if match else ""
        clean_title = re.sub(pattern, "", full_title).strip()

        # Description'ın başına JIRA ID'sini ekle
        formatted_description = f"## {jira_id}\n\n{description}"

        # Çözülmüş/kapalı durumları için kontrol
        is_closed = status.lower() in ["done", "released"]

        issue = {
            "title": clean_title,
            "description": formatted_description,
            "labels": [label.text for label in item.findall("labels/label")],
            "priority": item.find("priority").text,
            "status": status,
            "is_closed": is_closed,
            "repository": determine_repo(
                [label.text for label in item.findall("labels/label")]
            ),
        }
        issues.append(issue)

    return issues, len(valid_items)


def get_project_node_id(organization_name, project_number):
    time.sleep(0.5)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    query = """
    query{
        organization(login: "%s"){
            projectV2(number: %d) {
                id
            }
        }
    }
    """ % (
        organization_name,
        project_number,
    )

    response = requests.post(
        "https://api.github.com/graphql",
        headers=headers,
        json={"query": query},
    )

    if response.status_code == 200:
        result = response.json()
        return result["data"]["organization"]["projectV2"]["id"]
    else:
        raise Exception(f"Proje ID'si alınamadı: {response.text}")


def get_project_fields(project_node_id):
    time.sleep(0.5)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    query = (
        """
    query {
      node(id: "%s") {
        ... on ProjectV2 {
          fields(first: 20) {
            nodes {
              ... on ProjectV2Field {
                id
                name
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """
        % project_node_id
    )

    response = requests.post(
        "https://api.github.com/graphql", headers=headers, json={"query": query}
    )

    if response.status_code == 200:
        return response.json()["data"]["node"]["fields"]["nodes"]
    return None


def update_item_status(project_node_id, item_node_id, status):
    time.sleep(0.5)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Önce proje alanlarını al
    fields = get_project_fields(project_node_id)
    status_field = next((f for f in fields if f["name"] == "Status"), None)

    if status_field:
        # Status seçeneğini bul
        status_option = next(
            (
                opt
                for opt in status_field["options"]
                if opt["name"].lower() == status.lower()
            ),
            None,
        )

        if status_option:
            mutation = """
            mutation {
              updateProjectV2ItemFieldValue(
                input: {
                  projectId: "%s"
                  itemId: "%s"
                  fieldId: "%s"
                  value: {
                    singleSelectOptionId: "%s"
                  }
                }
              ) {
                projectV2Item {
                  id
                }
              }
            }
            """ % (
                project_node_id,
                item_node_id,
                status_field["id"],
                status_option["id"],
            )

            response = requests.post(
                "https://api.github.com/graphql",
                headers=headers,
                json={"query": mutation},
            )
            time.sleep(0.5)
            return response.status_code == 200
    return False


def get_existing_issues():
    time.sleep(0.5)

    """Mevcut issue'ların title'larını global setlere yükler"""
    g = Github(GITHUB_TOKEN)

    # Frontend repo için
    try:
        fe_repo = g.get_repo(REPO_FE)
        for issue in fe_repo.get_issues(state="all"):
            FE_ISSUE_TITLES.add(issue.title)
        time.sleep(0.5)
    except Exception as e:
        print(f"Frontend repo issue'ları alınırken hata: {e}")

    # Backend repo için
    try:
        be_repo = g.get_repo(REPO_BE)
        for issue in be_repo.get_issues(state="all"):
            BE_ISSUE_TITLES.add(issue.title)
        time.sleep(0.5)
    except Exception as e:
        print(f"Backend repo issue'ları alınırken hata: {e}")


def create_github_issues(issues, skip):
    g = Github(GITHUB_TOKEN)
    project_node_id = get_project_node_id("datarul", 1)

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    for index, issue in enumerate(issues, start=skip + 1):
        try:
            repo_name = issue["repository"]

            if repo_name == REPO_FE and issue["title"] in FE_ISSUE_TITLES:
                print(
                    f"{BLUE}[{index}] Bu issue zaten mevcut (Frontend): {issue['title']}{RESET}"
                )
                continue
            elif repo_name == REPO_BE and issue["title"] in BE_ISSUE_TITLES:
                print(
                    f"{BLUE}[{index}] Bu issue zaten mevcut (Backend): {issue['title']}{RESET}"
                )
                continue

            repo = g.get_repo(repo_name)

            github_issue = repo.create_issue(
                title=issue["title"],
                body=issue.get("description"),
                labels=[
                    label
                    for label in issue["labels"]
                    if label not in ["Frontend", "Backend"]
                ],
            )

            print(
                f"[{index}] Issue oluşturuldu: {issue['title']} - Status: {issue['status']}"
            )

            time.sleep(0.5)

            # Issue'yu projeye ekle
            mutation = """
            mutation {
              addProjectV2ItemById(input: {
                projectId: "%s"
                contentId: "%s"
              }) {
                item {
                  id
                }
              }
            }
            """ % (
                project_node_id,
                github_issue.raw_data["node_id"],
            )

            response = requests.post(
                "https://api.github.com/graphql",
                headers=headers,
                json={"query": mutation},
            )

            if response.status_code == 200:
                item_id = response.json()["data"]["addProjectV2ItemById"]["item"]["id"]
                # Status kontrolü ve güncelleme

                if issue["status"].lower() == "selected for development":
                    status = "Todo"
                else:
                    status = issue["status"]

                if not update_item_status(project_node_id, item_id, status):
                    print(
                        f"{RED}[{index}] Status güncellenemedi: {github_issue.title} - {status}{RESET}"
                    )

            if issue["is_closed"]:
                github_issue.edit(state="closed")

            time.sleep(0.5)

        except Exception as e:
            print(f"{RED}[{index}] Hata oluştu - '{issue['title']}': {e}{RESET}")


def main():
    # Önce mevcut issue'ları al
    get_existing_issues()
    print(f"Frontend'de {len(FE_ISSUE_TITLES)} mevcut issue bulundu")
    print(f"Backend'de {len(BE_ISSUE_TITLES)} mevcut issue bulundu")

    # JIRA XML dosyasının yolunu belirtin
    xml_file = "jira-issues.xml"

    # Sayfalama parametreleri
    skip = 0  # Kaç kayıt atlanacak
    take = 518  # Kaç kayıt alınacak

    # XML'i parse et
    issues, total_count = parse_jira_xml(xml_file, skip=skip, take=take)
    print(
        f"Toplam {total_count} issue'dan {skip}. kayıttan itibaren {len(issues)} tanesi alındı"
    )

    # GitHub'da issue'ları oluştur
    create_github_issues(issues, skip)


if __name__ == "__main__":
    main()
