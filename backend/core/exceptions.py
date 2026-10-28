from fastapi import HTTPException, status


class GitSummarizeError(Exception):
    """Base domain exception."""
    pass


class RepositoryNotFoundError(GitSummarizeError):
    def __init__(self, repo_id: str) -> None:
        self.repo_id = repo_id
        super().__init__(f"Repository {repo_id} not found")


class AnalysisNotFoundError(GitSummarizeError):
    def __init__(self, analysis_id: str) -> None:
        self.analysis_id = analysis_id
        super().__init__(f"Analysis {analysis_id} not found")


class RepositoryCloneError(GitSummarizeError):
    def __init__(self, url: str, reason: str) -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to clone {url}: {reason}")


class ParseError(GitSummarizeError):
    def __init__(self, file_path: str, reason: str) -> None:
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Parse error in {file_path}: {reason}")


class LLMError(GitSummarizeError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"LLM error: {reason}")


class StorageError(GitSummarizeError):
    def __init__(self, backend: str, reason: str) -> None:
        self.backend = backend
        self.reason = reason
        super().__init__(f"Storage error ({backend}): {reason}")


# HTTP helpers
def http_not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def http_bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def http_internal_error(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
