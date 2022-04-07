from pymedextcore.document import Document
from git import Repo,InvalidGitRepositoryError

import functools
import time
from logzero import logger
import re

def timer(func):
    """Print the runtime of the decorated function"""
    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()    # 1
        value = func(*args, **kwargs)
        end_time = time.perf_counter()      # 2
        run_time = end_time - start_time    # 3
        logger.info(f"Finished {func.__name__!r} in {run_time:.4f} secs")
        return value
    return wrapper_timer


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def to_chunks(lst, n):
    """List of sublists of size n form lst
    :param lst: List
    :param n: Integer
    :returns: List"""
    res = []
    for i in range(0,len(lst), n):
        res.append(lst[i:i+n])
    return res

def rawtext_loader(file): 
    with open(file) as f:
        txt = f.read()
        ID = re.search("([A-Za-z0-9]+)\.txt$", file)
        if not ID:
            ID = file
        else:
            ID  = ID.groups()[0]
    return Document(
        raw_text = txt,
        ID = ID,
        attributes = {'person_id': ID}
    )

def get_version_git(annotator, 
                    repo_name="equipe22/pymedext_eds"):
    try: 
        repo = Repo()
        commit = repo.commit('master').hexsha
        return f"{annotator}:{repo_name}:{commit}"
    except InvalidGitRepositoryError:
        return None