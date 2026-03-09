import pytest
import pickle
from zotero_arxiv_daily.protocol import Paper
from zotero_arxiv_daily.construct_email import render_email
from zotero_arxiv_daily.utils import send_email
@pytest.fixture
def papers() -> list[Paper]:
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author","Test Author 2"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="Test TLDR",
        affiliations=["Test Affiliation","Test Affiliation 2"],
        score=0.5
    )
    return [paper]*10

def test_render_email(papers:list[Paper]):
    email_content = render_email(papers)
    assert email_content is not None
    assert 'href="https://arxiv.org/abs/2512.04296"' in email_content
    assert 'href="https://arxiv.org/pdf/2512.04296"' in email_content
    assert ">ABS<" in email_content
    assert ">PDF<" in email_content

def test_render_email_with_acceptance_and_project_button():
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="Test TLDR",
        affiliations=["Test Affiliation"],
        acceptance_info="Accepted to CVPR 2026",
        project_url="https://github.com/example/project",
        score=8.0
    )
    email_content = render_email([paper])
    assert "Accepted: Accepted to CVPR 2026" in email_content
    assert 'href="https://github.com/example/project"' in email_content
    assert ">Project<" in email_content

def test_render_email_markdown_tldr():
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="第一行\n**重点结论**",
        affiliations=["Test Affiliation"],
        score=8.0
    )
    email_content = render_email([paper])
    assert "<br>" in email_content
    assert "<strong>重点结论</strong>" in email_content

def test_render_email_nested_unordered_list_tldr():
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="结论如下:\n- 一级要点A\n  - 二级要点A1\n- 一级要点B",
        affiliations=["Test Affiliation"],
        score=8.0
    )
    email_content = render_email([paper])
    assert "<ul>" in email_content
    assert email_content.count("<ul>") >= 2
    assert "<li>一级要点A" in email_content
    assert "<li>二级要点A1" in email_content
    assert "<li>一级要点B" in email_content

def test_render_email_nested_list_with_bold_content():
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="- 方法亮点：**动态路由**\n  - 关键收益：**延迟下降 30%**",
        affiliations=["Test Affiliation"],
        score=8.0
    )
    email_content = render_email([paper])
    assert "<ul>" in email_content
    assert "<li>方法亮点：<strong>动态路由</strong>" in email_content
    assert "<li>关键收益：<strong>延迟下降 30%</strong>" in email_content

def test_render_email_nested_star_list_tldr():
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="- 一级要点\n  * 二级星号要点",
        affiliations=["Test Affiliation"],
        score=8.0
    )
    email_content = render_email([paper])
    assert email_content.count("<ul>") >= 2
    assert "<li>一级要点" in email_content
    assert "<li>二级星号要点" in email_content

def test_render_email_unordered_with_ordered_sublist_tldr():
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="- 一级要点\n  1. 二级有序要点A\n  2. 二级有序要点B **重点**",
        affiliations=["Test Affiliation"],
        score=8.0
    )
    email_content = render_email([paper])
    assert "<ul>" in email_content
    assert "<ol>" in email_content
    assert "<li>二级有序要点A" in email_content
    assert "<li>二级有序要点B <strong>重点</strong>" in email_content

def test_render_email_ordered_with_unordered_sublist_tldr():
    paper = Paper(
        source="arxiv",
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test Abstract",
        url="https://arxiv.org/abs/2512.04296",
        pdf_url="https://arxiv.org/pdf/2512.04296",
        full_text="Test Full Text",
        tldr="1. 一级有序要点\n  - 二级无序要点A\n  - 二级无序要点B **重点**\n2. 一级有序要点二",
        affiliations=["Test Affiliation"],
        score=8.0
    )
    email_content = render_email([paper])
    assert "<ol>" in email_content
    assert "<ul>" in email_content
    assert "<li>一级有序要点" in email_content
    assert "<li>二级无序要点A" in email_content
    assert "<li>二级无序要点B <strong>重点</strong>" in email_content
    assert "<li>一级有序要点二" in email_content

def test_send_email(config,papers:list[Paper]):
    send_email(config, render_email(papers))
