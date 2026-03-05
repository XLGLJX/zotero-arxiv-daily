from .protocol import Paper
import math
import html
import re


framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em; /* 调整星星大小 */
      line-height: 1; /* 确保垂直对齐 */
      display: inline-flex;
      align-items: center; /* 保持对齐 */
    }
    .half-star {
      display: inline-block;
      width: 0.5em; /* 半颗星的宽度 */
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
To unsubscribe, remove your email in your Github Action setting.
</div>

</body>
</html>
"""

def get_empty_html():
  block_template = """
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        No Papers Today. Take a Rest!
    </td>
  </tr>
  </table>
  """
  return block_template

def get_block_html(title:str, authors:str, rate:str, tldr:str, pdf_url:str, affiliations:str=None):
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #666; padding: 8px 0;">
            {authors}
            <br>
            <i>{affiliations}</i>
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            {tldr}
        </td>
    </tr>

    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">PDF</a>
        </td>
    </tr>
</table>
"""
    return block_template.format(title=title, authors=authors,rate=rate, tldr=tldr, pdf_url=pdf_url, affiliations=affiliations)


def _format_inline_markdown(text: str) -> str:
    safe_text = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe_text, flags=re.DOTALL)


def _close_all_lists(parts: list[str], list_types: list[str], li_open: list[bool], current_level: int) -> int:
    for level in range(current_level, -1, -1):
        if li_open[level]:
            parts.append("</li>")
        parts.append(f"</{list_types[level]}>")
    list_types.clear()
    li_open.clear()
    return -1


def format_tldr_for_html(tldr: str | None) -> str:
    if tldr is None:
        return "No TLDR"

    lines = str(tldr).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unordered_pattern = re.compile(r"^(\s*)[-*]\s+(.*)$")
    ordered_pattern = re.compile(r"^(\s*)(\d+)[\.\)]\s+(.*)$")

    parts: list[str] = []
    list_types: list[str] = []
    li_open: list[bool] = []
    current_level = -1

    for raw_line in lines:
        line = raw_line.replace("\t", "    ")
        unordered_match = unordered_pattern.match(line)
        ordered_match = ordered_pattern.match(line)

        if unordered_match or ordered_match:
            if unordered_match:
                indent_len = len(unordered_match.group(1))
                item_text = _format_inline_markdown(unordered_match.group(2).strip())
                target_type = "ul"
            else:
                indent_len = len(ordered_match.group(1))
                item_text = _format_inline_markdown(ordered_match.group(3).strip())
                target_type = "ol"
            target_level = max(0, indent_len // 2)

            if current_level == -1:
                for level in range(target_level + 1):
                    list_type = target_type if level == target_level else "ul"
                    parts.append(f"<{list_type}>")
                    list_types.append(list_type)
                    li_open.append(False)
                current_level = target_level
            elif target_level > current_level:
                for level in range(current_level + 1, target_level + 1):
                    list_type = target_type if level == target_level else "ul"
                    parts.append(f"<{list_type}>")
                    list_types.append(list_type)
                    li_open.append(False)
                current_level = target_level
            elif target_level < current_level:
                for level in range(current_level, target_level, -1):
                    if li_open[level]:
                        parts.append("</li>")
                        li_open[level] = False
                    parts.append(f"</{list_types[level]}>")
                    li_open.pop()
                    list_types.pop()
                current_level = target_level
                if li_open[current_level]:
                    parts.append("</li>")
                    li_open[current_level] = False
            elif li_open[current_level]:
                parts.append("</li>")
                li_open[current_level] = False

            if list_types[current_level] != target_type:
                if li_open[current_level]:
                    parts.append("</li>")
                    li_open[current_level] = False
                parts.append(f"</{list_types[current_level]}>")
                list_types[current_level] = target_type
                parts.append(f"<{target_type}>")

            parts.append(f"<li>{item_text}")
            li_open[current_level] = True
            continue

        if current_level >= 0:
            current_level = _close_all_lists(parts, list_types, li_open, current_level)

        stripped = line.strip()
        if not stripped:
            parts.append("<br>")
        else:
            parts.append(_format_inline_markdown(stripped) + "<br>")

    if current_level >= 0:
        current_level = _close_all_lists(parts, list_types, li_open, current_level)

    return "".join(parts)

def get_stars(score:float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 6
    high = 8
    if score <= low:
        return ''
    elif score >= high:
        return full_star * 5
    else:
        interval = (high-low) / 10
        star_num = math.ceil((score-low) / interval)
        full_star_num = int(star_num/2)
        half_star_num = star_num - full_star_num * 2
        return '<div class="star-wrapper">'+full_star * full_star_num + half_star * half_star_num + '</div>'


def render_email(papers:list[Paper]) -> str:
    parts = []
    if len(papers) == 0 :
        return framework.replace('__CONTENT__', get_empty_html())
    
    for p in papers:
        #rate = get_stars(p.score)
        rate = round(p.score, 1) if p.score is not None else 'Unknown'
        author_list = [a for a in p.authors]
        num_authors = len(author_list)
        if num_authors <= 5:
            authors = ', '.join(author_list)
        else:
            authors = ', '.join(author_list[:3] + ['...'] + author_list[-2:])
        if p.affiliations is not None:
            affiliations = p.affiliations[:5]
            affiliations = ', '.join(affiliations)
            if len(p.affiliations) > 5:
                affiliations += ', ...'
        else:
            affiliations = 'Unknown Affiliation'
        tldr = format_tldr_for_html(p.tldr)
        parts.append(get_block_html(p.title, authors, rate, tldr, p.pdf_url, affiliations))

    content = '<br>' + '</br><br>'.join(parts) + '</br>'
    return framework.replace('__CONTENT__', content)
