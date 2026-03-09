from .base import BaseRetriever, register_retriever
import arxiv
from arxiv import Result as ArxivResult
from ..protocol import Paper
from ..utils import extract_markdown_from_pdf, extract_tex_code_from_tar
from tempfile import TemporaryDirectory
import feedparser
from urllib.request import urlretrieve
from tqdm import tqdm
import os
import re
from loguru import logger


_URL_PATTERN = re.compile(r"https?://[^\s<>\]\)\"']+", flags=re.IGNORECASE)
_ACCEPTED_PATTERN = re.compile(
    r"\b(accepted|acceptance|to appear|in proceedings of|camera[- ]ready|oral|spotlight)\b",
    flags=re.IGNORECASE,
)
_NOT_ACCEPTED_PATTERN = re.compile(
    r"\b(under review|under submission|submitted to)\b",
    flags=re.IGNORECASE,
)
_PROJECT_KEYWORD_PATTERN = re.compile(
    r"\b(project page|project website|project site|code|github|implementation|open[- ]source|demo|online demo|interactive demo)\b",
    flags=re.IGNORECASE,
)


def _clean_url(url: str) -> str:
    return url.rstrip(".,;:)]}'\"")


def parse_project_url_from_text(text: str | None) -> str | None:
    if not text:
        return None

    normalized_text = " ".join(text.split())
    lower_text = normalized_text.lower()

    keyword_url_match = re.search(
        r"(project page|project website|project site|code|github|implementation|open[- ]source|demo|online demo|interactive demo)\s*[:：]\s*(https?://[^\s<>\]\)\"']+)",
        normalized_text,
        flags=re.IGNORECASE,
    )
    if keyword_url_match:
        return _clean_url(keyword_url_match.group(2))

    urls = [_clean_url(url) for url in _URL_PATTERN.findall(normalized_text)]
    if not urls:
        return None

    github_url = next((u for u in urls if "github.com" in u.lower()), None)
    if github_url:
        return github_url

    if _PROJECT_KEYWORD_PATTERN.search(lower_text):
        return urls[0]

    return None


def parse_arxiv_comments(comment: str | None) -> tuple[str | None, str | None]:
    if not comment:
        return None, None

    normalized_comment = " ".join(comment.split())

    acceptance_info = None
    if _ACCEPTED_PATTERN.search(normalized_comment) and not _NOT_ACCEPTED_PATTERN.search(normalized_comment):
        acceptance_info = normalized_comment

    project_url = parse_project_url_from_text(normalized_comment)
    return acceptance_info, project_url


@register_retriever("arxiv")
class ArxivRetriever(BaseRetriever):
    def __init__(self, config):
        super().__init__(config)
        if self.config.source.arxiv.category is None:
            raise ValueError("category must be specified for arxiv.")
    def _retrieve_raw_papers(self) -> list[ArxivResult]:
        client = arxiv.Client(num_retries=10,delay_seconds=10)
        query = '+'.join(self.config.source.arxiv.category)
        # Get the latest paper from arxiv rss feed
        feed = feedparser.parse(f"https://rss.arxiv.org/atom/{query}")
        if 'Feed error for query' in feed.feed.title:
            raise Exception(f"Invalid ARXIV_QUERY: {query}.")
        raw_papers = []
        all_paper_ids = [i.id.removeprefix("oai:arXiv.org:") for i in feed.entries if i.get("arxiv_announce_type","new") == 'new']
        if self.config.executor.debug:
            all_paper_ids = all_paper_ids[:10]

        # Get full information of each paper from arxiv api
        bar = tqdm(total=len(all_paper_ids))
        for i in range(0,len(all_paper_ids),20):
            search = arxiv.Search(id_list=all_paper_ids[i:i+20])
            batch = list(client.results(search))
            bar.update(len(batch))
            raw_papers.extend(batch)
        bar.close()

        return raw_papers

    def convert_to_paper(self, raw_paper:ArxivResult) -> Paper:
        title = raw_paper.title
        authors = [a.name for a in raw_paper.authors]
        abstract = raw_paper.summary
        pdf_url = raw_paper.pdf_url
        acceptance_info, project_url_comment = parse_arxiv_comments(raw_paper.comment)
        project_url_abstract = parse_project_url_from_text(abstract)
        project_url = project_url_comment or project_url_abstract
        full_text = extract_text_from_pdf(raw_paper)
        if full_text is None:
            full_text = extract_text_from_tar(raw_paper)
        return Paper(
            source=self.name,
            title=title,
            authors=authors,
            abstract=abstract,
            url=raw_paper.entry_id,
            pdf_url=pdf_url,
            full_text=full_text,
            acceptance_info=acceptance_info,
            project_url=project_url,
        )

def extract_text_from_pdf(paper: ArxivResult) -> str | None:
    with TemporaryDirectory() as temp_dir:
        path = os.path.join(temp_dir, "paper.pdf")
        if paper.pdf_url is None:
            logger.warning(f"No PDF URL available for {paper.title}")
            return None
        urlretrieve(paper.pdf_url, path)
        try:
            full_text = extract_markdown_from_pdf(path)
        except Exception as e:
            logger.warning(f"Failed to extract full text of {paper.title} from pdf: {e}")
            full_text = None
        return full_text

def extract_text_from_tar(paper: ArxivResult) -> str | None:
    with TemporaryDirectory() as temp_dir:
        path = os.path.join(temp_dir, "paper.tar.gz")
        source_url = paper.source_url()
        if source_url is None:
            logger.warning(f"No source URL available for {paper.title}")
            return None
        urlretrieve(source_url, path)
        try:
            file_contents = extract_tex_code_from_tar(path, paper.entry_id)
            if "all" not in file_contents:
                logger.warning(f"Failed to extract full text of {paper.title} from tar: Main tex file not found.")
                return None
            full_text = file_contents["all"]
        except Exception as e:
            logger.warning(f"Failed to extract full text of {paper.title} from tar: {e}")
            full_text = None
        return full_text
