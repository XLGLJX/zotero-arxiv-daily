from zotero_arxiv_daily.retriever.arxiv_retriever import parse_arxiv_comments, parse_project_url_from_text


def test_parse_arxiv_comments_extracts_accepted_and_project_url():
    comment = (
        "Accepted to CVPR 2026. "
        "Project page: https://example.com/project . "
        "Code: https://github.com/example/repo"
    )
    acceptance_info, project_url = parse_arxiv_comments(comment)
    assert acceptance_info is not None
    assert "Accepted to CVPR 2026" in acceptance_info
    assert project_url == "https://example.com/project"


def test_parse_arxiv_comments_ignores_non_accepted_submission():
    comment = "Submitted to ICLR 2026. Code: https://github.com/example/repo"
    acceptance_info, project_url = parse_arxiv_comments(comment)
    assert acceptance_info is None
    assert project_url == "https://github.com/example/repo"


def test_parse_project_url_from_abstract_with_keyword():
    abstract = "We release our code at: https://example.org/my-project and provide full implementation details."
    project_url = parse_project_url_from_text(abstract)
    assert project_url == "https://example.org/my-project"


def test_parse_project_url_from_abstract_with_github_link():
    abstract = "Our method improves SOTA. https://github.com/example/repo"
    project_url = parse_project_url_from_text(abstract)
    assert project_url == "https://github.com/example/repo"


def test_parse_project_url_from_demo_keyword():
    abstract = "Demo: https://example.com/demo-page"
    project_url = parse_project_url_from_text(abstract)
    assert project_url == "https://example.com/demo-page"
