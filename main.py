#!/usr/bin/env python3
"""
Browsecomp-V3 主入口

Browsecomp风格复杂问题生成器
"""

import logging
import sys
import argparse
from pathlib import Path

from browsecomp_v3.core.config import Config, get_config
from browsecomp_v3.templates.template_selector import TemplateSelector
from browsecomp_v3.constraints.constraint_generator import ConstraintGenerator
from browsecomp_v3.graph.kg_loader import KnowledgeGraphLoader
from browsecomp_v3.graph.query_executor import QueryExecutor
from browsecomp_v3.generator.question_generator import QuestionGenerator
from browsecomp_v3.generator.answer_extractor import AnswerExtractor
from browsecomp_v3.validator.question_validator import QuestionValidator
from browsecomp_v3.validator.diversity_checker import DiversityChecker
from browsecomp_v3.output.exporter import Exporter
from browsecomp_v3.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def generate_questions(
    count: int = 50,
    min_constraints: int = 1,
    max_constraints: int = 1,
    template_id: str = None,
    output_format: str = "both"
):
    """
    生成复杂问题

    Args:
        count: 生成数量
        min_constraints: 最小约束数
        max_constraints: 最大约束数
        template_id: 指定模板ID
        output_format: 输出格式 (json/markdown/both)
    """
    from rich.console import Console
    from rich.progress import Progress

    console = Console()
    config = get_config()

    console.print(f"[bold cyan]Browsecomp-V3 复杂问题生成器[/bold cyan]")
    console.print(f"配置:")
    console.print(f"  - 知识图谱: {config.kg_path}")
    console.print(f"  - 生成数量: {count}")
    console.print(f"  - 约束范围: {min_constraints}-{max_constraints}")
    console.print(f"  - 输出格式: {output_format}")
    console.print()

    # 初始化组件
    template_selector = TemplateSelector()
    kg_loader = KnowledgeGraphLoader()
    constraint_generator = ConstraintGenerator(kg_loader)  # 传入kg_loader
    query_executor = QueryExecutor(kg_loader)
    question_generator = QuestionGenerator(kg_loader)
    answer_extractor = AnswerExtractor()
    question_validator = QuestionValidator()
    diversity_checker = DiversityChecker()
    exporter = Exporter()

    # 加载知识图谱
    with console.status("[bold green]加载知识图谱..."):
        kg_loader.load()
    console.print(f"[green]✓[/green] 知识图谱已加载: {kg_loader.node_count} 节点, {kg_loader.edge_count} 边")
    console.print()

    # 生成问题
    generated_questions = []
    retries = 0
    max_retries = config.max_generation_retries

    with Progress() as progress:
        task = progress.add_task("[cyan]生成问题...", total=count)

        while len(generated_questions) < count and retries < max_retries * count:
            # 1. 选择模板
            tid = template_selector.select(mode="random" if template_id is None else "specific", template_id=template_id)

            # 2. 生成约束（约束过滤已在ConstraintGenerator内部处理）
            try:
                constraint_set = constraint_generator.generate(
                    template_id=tid,
                    min_constraints=min_constraints,
                    max_constraints=max_constraints
                )

                # Debug output
                if config.verbose:
                    constraint = constraint_set.constraints[0]
                    console.print(f"  [dim]模板:{tid}, {constraint.constraint_type}: {constraint.filter_condition}[/dim]")

            except Exception as e:
                if config.verbose:
                    console.print(f"  [dim]约束生成失败: {e}[/dim]")
                retries += 1
                continue

            # 3. 执行查询
            try:
                query_result = query_executor.execute(constraint_set)

                if config.verbose:
                    console.print(f"  [dim]  -> 查询结果: {len(query_result.candidates)} 候选[/dim]")

                if len(query_result.candidates) == 0:
                    retries += 1
                    continue

                # 如果有多个候选，随机选一个
                if len(query_result.candidates) > 1:
                    import random
                    candidate_id = random.choice(query_result.candidates)
                else:
                    candidate_id = query_result.candidates[0]

            except Exception as e:
                if config.verbose:
                    console.print(f"  [dim]  -> 查询失败: {e}[/dim]")
                retries += 1
                continue

            # 4. 提取答案
            try:
                candidate_data = kg_loader.get_node(candidate_id)
                answer = answer_extractor.extract(candidate_id, candidate_data, kg_loader)

                if config.verbose:
                    console.print(f"  [dim]  -> 答案提取: {answer.text[:30]}...[/dim]")
            except Exception as e:
                if config.verbose:
                    console.print(f"  [dim]  -> 答案提取失败: {e}[/dim]")
                retries += 1
                continue

            # 5. 生成问题
            try:
                question = question_generator.generate(
                    constraint_set=constraint_set,
                    reasoning_chain=query_result.reasoning_chain,
                    answer_entity_id=candidate_id,
                    answer_text=answer.text
                )

                if config.verbose:
                    console.print(f"  [dim]  -> 问题生成成功: {question.question_id}[/dim]")
            except Exception as e:
                if config.verbose:
                    console.print(f"  [dim]  -> 问题生成失败: {e}[/dim]")
                retries += 1
                continue

            # 6. 验证
            if question_validator.validate(question, query_result.candidates):
                generated_questions.append(question)
                progress.update(task, advance=1)
                console.print(f"[green]✓[/green] 生成问题 {len(generated_questions)}/{count}: {question.question_id}")

    # 统计信息
    console.print()
    console.print(f"[bold]生成完成:[/bold]")
    console.print(f"  - 成功: {len(generated_questions)} 个")
    console.print(f"  - 重试: {retries} 次")
    console.print()

    # 多样性分析
    diversity_stats = diversity_checker.check_diversity(generated_questions)
    console.print(f"[bold]多样性统计:[/bold]")
    console.print(f"  - 唯一问题: {diversity_stats['unique']}")
    console.print(f"  - 多样性率: {diversity_stats['diversity_rate']:.1%}")
    console.print(f"  - 模板分布: {diversity_stats['template_distribution']}")
    console.print()

    # 导出
    with console.status("[bold green]导出问题..."):
        output_paths = exporter.export_both(generated_questions) if output_format == "both" else \
                       {"json": exporter.export_json(generated_questions)} if output_format == "json" else \
                       {"markdown": exporter.export_markdown(generated_questions)}

    for fmt, path in output_paths.items():
        console.print(f"[green]✓[/green] {fmt.upper()} 已导出: {path}")

    return generated_questions


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Browsecomp-V3 复杂学术问题生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成50个问题
  %(prog)s --count 50

  # 使用指定模板生成
  %(prog)s --template A --count 20

  # 只输出JSON格式
  %(prog)s --format json
        """
    )

    parser.add_argument(
        "-c", "--count",
        type=int,
        default=50,
        help="生成问题数量 (默认: 50)"
    )

    parser.add_argument(
        "--min-constraints",
        type=int,
        default=1,
        help="最小约束数量 (默认: 1)"
    )

    parser.add_argument(
        "--max-constraints",
        type=int,
        default=1,
        help="最大约束数量 (默认: 1)"
    )

    parser.add_argument(
        "-t", "--template",
        type=str,
        choices=["A", "B", "C", "D", "E", "F", "G"],
        help="指定模板ID (默认: 随机)"
    )

    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["json", "markdown", "both"],
        default="both",
        help="输出格式 (默认: both)"
    )

    parser.add_argument(
        "--kg-path",
        type=str,
        help="知识图谱文件路径"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出"
    )

    args = parser.parse_args()

    # 设置配置
    config = get_config()
    if args.kg_path:
        config.kg_path = args.kg_path
    if args.verbose:
        config.verbose = True
        config.log_level = "DEBUG"

    # 设置日志
    setup_logging(
        log_level=config.log_level,
        log_file="browsecomp.log",
        log_dir=config.output_dir / "logs",
        verbose=config.verbose
    )

    logger.info("Starting Browsecomp-V3 question generation")
    logger.info(f"Configuration: count={args.count}, constraints={args.min_constraints}-{args.max_constraints}, "
                f"template={args.template or 'random'}, format={args.format}")

    # 生成问题
    try:
        generate_questions(
            count=args.count,
            min_constraints=args.min_constraints,
            max_constraints=args.max_constraints,
            template_id=args.template,
            output_format=args.format
        )
        logger.info("Question generation completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Error during question generation: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
