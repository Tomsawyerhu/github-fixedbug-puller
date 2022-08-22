import datetime
import json
import re

import requests
from bs4 import BeautifulSoup

from model import FixedBug, CodeDiff

website = "github.com"
group_ids = ["tensorflow", "pytorch"]
artifact_ids_list = [["tensorflow"], ["pytorch"]]

sensitive_texts = ["fix", "defect", "error", "bug", "issue", "mistake", "correct", "fault", "flaw"]
diff_file_types = [".cc", ".c", ".py", ".java", ".cpp"]
time_span = datetime.datetime.strptime("2022-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
page_limit = [0,1,2,3,4,5,6,7,8,9,]
fixed_bugs = []
output = "./pull.json"


# os.environ['NO_PROXY'] = website


def find_open_ids(soup: BeautifulSoup):
    oids = soup.find_all(class_="opened-by")  # open id
    result = []
    for oid in oids:
        txt = oid.text
        t = int(txt.strip().split('\n')[0].strip()[1:])
        result.append(t)
    return result


def find_title(soup: BeautifulSoup, oid: int):
    return soup.find("a", id="issue_{}_link".format(oid)).text


def find_labels(soup: BeautifulSoup, oid: int):
    labs = soup.find(id="issue_{}".format(oid)).find_all("a", id=re.compile("label-[A-za-z0-9]*"))
    result = []
    for lab in labs:
        result.append(lab.text.strip())
    return result


def find_closed_time(soup: BeautifulSoup, oid: int):
    return soup.find(id="issue_{}".format(oid)).find("relative-time")["datetime"]


def find_code_diffs(soup: BeautifulSoup):
    result = []
    root = soup.find(id="files").find(class_="js-diff-progressive-container")
    for diff_code in root.findChildren(id=re.compile("diff-[a-z0-9]*"), recursive=False):
        file_type = diff_code["data-file-type"]
        print(file_type)
        if file_type not in diff_file_types:
            continue
        # where is the file
        code_dir = diff_code.find(class_="Truncate").a["title"]
        if "test" in code_dir:
            continue

        # diff table
        code1 = ""
        code2 = ""
        diff_table = diff_code.find("table")
        method = None
        for tr in diff_table.tbody.find_all("tr"):
            td = list(tr.find_all("td"))[-1]
            if "@@" in td.text:
                if method is not None:
                    cf = CodeDiff(file_type, code_dir, code1, code2)
                    cf.method_name = method
                    result.append(cf)
                    # clear
                    code1 = ""
                    code2 = ""
                # method name
                method = td.text.split("@@")[-1].strip()
            elif len(list(tr.find_all("td"))) == 3:

                td = list(tr.find_all("td"))[2]
                # deleted row
                if "blob-code-deletion" in td["class"]:
                    code1 += td.span.text

                # new added row
                elif "blob-code-addition" in td["class"]:
                    code2 += td.span.text

                # plain row
                else:
                    code1 += td.span.text
                    code2 += td.span.text
        if method is not None:
            cf = CodeDiff(file_type, code_dir, code1, code2)
            cf.method_name = method
            result.append(cf)
    return result


if __name__ == '__main__':
    for i in range(len(group_ids)):
        group_id = group_ids[i]
        artifact_ids = artifact_ids_list[i]
        for artifact_id in artifact_ids:
            for j in page_limit:
                url = "http://{}/{}/{}/pulls?".format(website, group_id, artifact_id)
                params = dict()
                params["page"] = j + 1
                params["q"] = "is:pr is:closed"
                # params["q"] = unquote(params["q"])

                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, "
                                  "like Gecko) Version/15.5 Safari/605.1.15",
                    "Accept-Language": "zh-CN,zh-Hans;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive"
                }
                response = requests.get(url=url, params=params)

                if response.status_code != 200:
                    break

                # 获取该页上的open_id
                s = BeautifulSoup(response.content, "lxml")
                open_ids = find_open_ids(s)

                for open_id in open_ids:
                    # filter by title and tags
                    title = find_title(s, open_id)  # get title
                    labels = find_labels(s, open_id)  # get labels
                    should_filter = True
                    for sensitive_text in sensitive_texts:
                        if title.find(sensitive_text) >= 0 or len(
                                list(filter(lambda x: x.find(sensitive_text) >= 0, labels))) > 0:
                            should_filter = False
                            break
                    if should_filter:
                        continue
                    # for those pulls which remain, find closed time
                    closed_time = find_closed_time(s, open_id)
                    utc = datetime.datetime.strptime(closed_time, "%Y-%m-%dT%H:%M:%SZ")
                    if utc < time_span:
                        continue
                    # print(closed_time)

                    # for those pulls which remain, extract code before and after bug fix
                    url = "http://{}/{}/{}/pull/{}/files".format(website, group_id, artifact_id, open_id)
                    fchange_response = requests.get(url)
                    ss = BeautifulSoup(fchange_response.content, "lxml")
                    codes = find_code_diffs(ss)

                    fixed_bug = FixedBug(group_id, artifact_id, open_id, title, labels)
                    fixed_bug.code_diffs = codes
                    fixed_bug.closed_time = closed_time
                    fixed_bugs.append(fixed_bug)
    # 持久化
    with open(output, encoding="utf8", mode='w') as f:
        f.write(json.dumps([x.__dict__() for x in fixed_bugs], indent=1))
        f.flush()
        f.close()
