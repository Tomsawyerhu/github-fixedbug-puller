class FixedBug:
    __accepted_attributes = ["group_id", "artifact_id", "oid", "cid", "commit_msg", "commit_date", "title", "tags",
                             "closed_time", "code_diffs"]

    def __init__(self, gid, aid, oid, title, tags):
        self.group_id = gid
        self.artifact_id = aid
        self.oid = oid
        self.title = title
        self.tags = tags

    def __dict__(self):
        result = dict()
        for a in FixedBug.__accepted_attributes:
            avalue = getattr(self, a,None)
            if avalue is not None:
                if a == "code_diffs":
                    result[a] = [v.__dict__() for v in avalue]
                else:
                    result[a] = avalue
        return result


class CodeDiff:
    __accepted_attributes = ["language", "dir", "code1", "code2", "method_name"]

    def __init__(self, language, dir, code1, code2):
        self.language = language
        self.dir = dir
        self.code1 = code1
        self.code2 = code2

    def __dict__(self):
        result = dict()
        for a in CodeDiff.__accepted_attributes:
            avalue = getattr(self, a,None)
            if avalue is not None:
                result[a] = avalue
        return result


class Commit:
    def __init__(self, commit_id=None, commit_date=None, commit_message=None, is_bugfix=None):
        self.commit_id = commit_id
        self.commit_date = commit_date
        self.commit_message = commit_message
        self.is_bugfix = is_bugfix
