from dataclasses import dataclass
from typing import Optional, TypeVar
from datetime import datetime
import ast
import re
import tiktoken
from openai import OpenAI
from loguru import logger
import json
RawPaperItem = TypeVar('RawPaperItem')

@dataclass
class Paper:
    source: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: Optional[str] = None
    full_text: Optional[str] = None
    tldr: Optional[str] = None
    affiliations: Optional[list[str]] = None
    acceptance_info: Optional[str] = None
    project_url: Optional[str] = None
    score: Optional[float] = None

    def _parse_affiliations_response(self, raw_affiliations: object) -> list[str]:
        if raw_affiliations is None:
            return []

        if isinstance(raw_affiliations, list):
            candidate = raw_affiliations
        else:
            text = str(raw_affiliations).strip()
            if not text:
                return []

            candidates = [text]
            candidates.extend(re.findall(r'\[[\s\S]*?\]', text))

            candidate = None
            for item in candidates:
                parsed_item = None
                try:
                    parsed_item = json.loads(item)
                except Exception:
                    try:
                        parsed_item = ast.literal_eval(item)
                    except Exception:
                        continue

                if isinstance(parsed_item, list):
                    candidate = parsed_item
                    break

            if candidate is None:
                return []

        affiliations: list[str] = []
        seen: set[str] = set()
        for item in candidate:
            affiliation = str(item).strip()
            if not affiliation or affiliation in seen:
                continue
            seen.add(affiliation)
            affiliations.append(affiliation)

        return affiliations

    def _generate_tldr_with_llm(self, openai_client:OpenAI,llm_params:dict) -> str:
        lang = llm_params.get('language', 'English')
        # prompt = f"Given the following information about a paper, generate a one-sentence TLDR summary in {lang}:\n\n"
        prompt = f"""
[输出格式]
一. 基础信息

**论文标题**： [中文译名]

**Keywords**： (3-5个，如：LLM Safety，Backdoor，Image Injection)

**TLDR**： (点破核心设计)

**泛读关键**：（如果我只通过这次总结阅读这篇论文一遍，我需要学习到这篇论文什么样的核心设计即可）

二. 性质判定与总结

请根据判定的性质（选其一），填充对应模版，语言凝练的进行总结：

🗡️ **安全攻击**： - 攻击向量: \n - 攻击方案: \n - 攻击类别: \n - 攻击目标: \n

🛡️ **安全保护**： - 针对攻击方式: \n - 防御方案: \n - 防御类别: \n - 防御对象: \n

🤖 **AI 基础模型**： - 模型类别: \n - 核心架构改进: \n - 训练范式: \n - 能力边界: \n

🏗️ **新颖框架**： - 系统架构: \n - 解决痛点: \n - 工作流逻辑。

🧪 **新算法新设计**： - 类别/定位: \n - 算法背景: \n - 改进目标: \n - 核心改进点。

📚 **综述**： - 分类体系: \n - 未来趋势。

📊 **数据集/Benchmark**： - 来源与规模: \n - 构建逻辑: \n - 评测指标: \n - 解决痛点: \n

🌀 **其他**： - [请仿照上述逻辑自拟短语模版]。
        \n\n"""
        if self.title:
            prompt += f"Title:\n {self.title}\n\n"

        if self.abstract:
            prompt += f"Abstract: {self.abstract}\n\n"

        if self.full_text:
            prompt += f"Preview of main content:\n {self.full_text}\n\n"

        if not self.full_text and not self.abstract:
            logger.warning(f"Neither full text nor abstract is provided for {self.url}")
            return "Failed to generate TLDR. Neither full text nor abstract is provided"
        
        # use gpt-4o tokenizer for estimation
        enc = tiktoken.encoding_for_model("gpt-4o")
        prompt_tokens = enc.encode(prompt)
        # prompt_tokens = prompt_tokens[:4000]  # truncate to 4000 tokens
        prompt_tokens = prompt_tokens[:20000]  # truncate to 4000 tokens
        prompt = enc.decode(prompt_tokens)
        
        response = openai_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    # "content": f"You are an assistant who perfectly summarizes scientific paper, and gives the core idea of the paper to the user. Your answer should be in {lang}.",
                    "content": f"""
                    你是一位计算机、人工智能、具身智能、网络安全的资深研究员。你的任务是帮用户解析论文，介绍核心思想， 你的回答应为 {lang} 语言。
                    Requirements:
                    语言凝练简介，如果一句话可以讲清楚，我得到的就是一句话。
                    格式清晰，适当换行与加粗。
                    分类映射： 必须首先判定论文性质，并严格匹配对应的总结模版。
                    建立索引： 为论文生成 3-5 个精准关键词。"""
                },
                {"role": "user", "content": prompt},
            ],
            **llm_params.get('generation_kwargs', {})
        )
        tldr = response.choices[0].message.content
        return tldr
    
    def generate_tldr(self, openai_client:OpenAI,llm_params:dict) -> str:
        try:
            tldr = self._generate_tldr_with_llm(openai_client,llm_params)
            self.tldr = tldr
            return tldr
        except Exception as e:
            logger.warning(f"Failed to generate tldr of {self.url}: {e}")
            tldr = self.abstract
            self.tldr = tldr
            return tldr

    def _generate_affiliations_with_llm(self, openai_client:OpenAI,llm_params:dict) -> Optional[list[str]]:
        if self.full_text is not None:
            prompt = f"Given the beginning of a paper, extract the affiliations of the authors in a python list format, which is sorted by the author order. If there is no affiliation found, return an empty list '[]':\n\n{self.full_text}"
            # use gpt-4o tokenizer for estimation
            enc = tiktoken.encoding_for_model("gpt-4o")
            prompt_tokens = enc.encode(prompt)
            prompt_tokens = prompt_tokens[:2000]  # truncate to 2000 tokens
            prompt = enc.decode(prompt_tokens)
            generation_kwargs = dict(llm_params.get('generation_kwargs', {}))
            generation_kwargs.update(llm_params.get('affiliations_generation_kwargs', {}))
            affiliations = openai_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an assistant who perfectly extracts affiliations of authors from a paper. You should return a python list of affiliations sorted by the author order, like [\"TsingHua University\",\"Peking University\"]. If an affiliation is consisted of multi-level affiliations, like 'Department of Computer Science, TsingHua University', you should return the top-level affiliation 'TsingHua University' only. Do not contain duplicated affiliations. If there is no affiliation found, you should return an empty list [ ]. You should only return the final list of affiliations, and do not return any intermediate results.",
                    },
                    {"role": "user", "content": prompt},
                ],
                **generation_kwargs
            )
            affiliations = affiliations.choices[0].message.content

            affiliations = self._parse_affiliations_response(affiliations)

            return affiliations
    
    def generate_affiliations(self, openai_client:OpenAI,llm_params:dict) -> Optional[list[str]]:
        try:
            affiliations = self._generate_affiliations_with_llm(openai_client,llm_params)
            self.affiliations = affiliations
            return affiliations
        except Exception as e:
            logger.warning(f"Failed to generate affiliations of {self.url}: {e}")
            self.affiliations = None
            return None
@dataclass
class CorpusPaper:
    title: str
    abstract: str
    added_date: datetime
    paths: list[str]
