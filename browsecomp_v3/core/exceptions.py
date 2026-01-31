"""
Browsecomp-V3 异常定义

定义系统中使用的所有异常类型。
"""


class BrowsecompException(Exception):
    """Browsecomp-V3 基础异常"""
    pass


class TemplateNotFoundException(BrowsecompException):
    """模板未找到异常"""
    pass


class ConstraintParseException(BrowsecompException):
    """约束解析异常"""
    pass


class GraphTraversalException(BrowsecompException):
    """图遍历异常"""
    pass


class QuestionGenerationException(BrowsecompException):
    """问题生成异常"""
    pass


class ValidationException(BrowsecompException):
    """验证异常"""
    pass


class KnowledgeGraphException(BrowsecompException):
    """知识图谱异常"""
    pass
