import datetime
import json
import os

from model import Commit, CodeDiff, FixedBug

commits = []
fixed_bugs = []
sensitive_texts = ["fix", "defect", "error", "bug", "issue", "mistake", "correct", "fault", "flaw"]
diff_file_types = [".cc", ".c", ".py", ".java", ".cpp"]
self_root = os.path.dirname(__file__)
project_root_path = "/root/pytorch"
gid = "pytorch"
aid = "pytorch"
output = "commit.json"
time_span = datetime.datetime.strptime("2022-01-01 00:00:00 +0000", "%Y-%m-%d %H:%M:%S %z")


# run "git log --pretty=format:"%H%n%ci%n%s%n%n" >commit.txt" under project root path
def git_log():
    global project_root_path
    os.system("cd {}".format(
        project_root_path) + " && git log --pretty=format:\"%H%n%ci%n%s%n%n\" >{}/commit.txt".format(self_root))


def handle_commit_log():
    global sensitive_texts
    line_num = 0
    with open("./git-log/commit.txt", 'r', encoding='utf8') as f:
        current_commit = None
        for line in f.readlines():
            # commit id
            if line_num % 4 == 0:
                current_commit = Commit()
                current_commit.commit_id = line.strip()
            # commit date
            elif line_num % 4 == 1:
                current_commit.commit_date = datetime.datetime.strptime(line.strip(), "%Y-%m-%d %H:%M:%S %z")
            # commit message
            elif line_num % 4 == 2:
                current_commit.commit_message = line.strip()
                current_commit.is_bugfix = (len(list(filter(lambda x: x in line.strip(), sensitive_texts))) > 0)
            else:
                commits.append(current_commit)
            line_num += 1
        f.close()


def commit_diff():
    global commits, project_root_path, fixed_bugs, gid, aid
    for i in range(len(commits)):
        if commits[i].is_bugfix and commits[i].commit_date > time_span:
            commit_id = commits[i].commit_id
            # git diff
            os.system("cd {}".format(
                project_root_path) + " && git show {} > {}/git-log/diff.txt".format(commit_id,
                                                                                    self_root))
            # read git diff file
            code_diff = _read_git_diff()
            fixed_bug = FixedBug(gid=gid, aid=aid, oid=None, title=None, tags=None)
            fixed_bug.cid = commits[i].commit_id
            fixed_bug.commit_msg = commits[i].commit_message
            fixed_bug.commit_date = commits[i].commit_date.strftime("%Y-%m-%d %H:%M:%S")
            fixed_bug.code_diffs = code_diff
            fixed_bugs.append(fixed_bug)


def _read_git_diff():
    global diff_file_types
    gformat = "diff --git"
    result = []
    with open("./git-log/diff.txt", 'r', encoding='utf8') as f:
        code_diff = None
        skip = True
        flag = 0  # 标记需要跳过的行数
        file_dir = ""
        language = ""
        code1 = ""
        code2 = ""
        for line in f.readlines():
            if line.startswith(gformat):  # diff --git ...
                if code_diff is not None:
                    code_diff.code1 = code1
                    code_diff.code2 = code2
                    result.append(code_diff)
                    # clear
                    code_diff = None
                    file_dir = ""
                    language = ""
                    code1 = ""
                    code2 = ""
                file_dir = line.split(" ")[-1][2:].strip()
                if "test" in file_dir or file_dir.rfind(".") < 0 or file_dir[file_dir.rfind("."):] not in diff_file_types:
                    skip = True
                    language = "unknown"
                else:
                    skip=False
                if not skip:
                    language = file_dir[file_dir.rfind("."):]
                    flag = 1
            elif not skip:
                if flag <= 3:
                    pass
                else:
                    line = line.strip()
                    if len(line) == 0:
                        pass
                    elif line.startswith("+"):
                        code2 += line[1:]
                        code2 += "\n"
                    elif line.startswith("-"):
                        code1 += line[1:]
                        code1 += "\n"
                    elif "@@" not in line:
                        code1 += line
                        code1 += "\n"
                        code2 += line
                        code2 += "\n"
                    else:
                        if code_diff is not None:
                            code_diff.code1 = code1
                            code_diff.code2 = code2
                            result.append(code_diff)
                            # clear
                            code_diff = None
                            code1 = ""
                            code2 = ""
                        code_diff = CodeDiff(language=language, dir=file_dir, code1=None, code2=None)
                        code_diff.method_name = line[line.rfind("@@") + 2:].strip()
                flag += 1
        if code_diff is not None:
            code_diff.code1 = code1
            code_diff.code2 = code2
            result.append(code_diff)
        f.close()
    return result


if __name__ == '__main__':
    git_log()
    handle_commit_log()
    commit_diff()
    # 持久化
    with open(output, encoding="utf8", mode='w') as ff:
        ff.write(json.dumps([x.__dict__() for x in fixed_bugs], indent=1))
        ff.flush()
        ff.close()
