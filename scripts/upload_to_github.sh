#!/bin/bash
#
# 上传代码到GitHub仓库
# 用法: ./scripts/upload_to_github.sh [message]
#

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# GitHub仓库配置
GITHUB_REPO="lzyq-hntvu/browsecomp-V3"
GITHUB_URL_BASE="https://github.com/${GITHUB_REPO}.git"

# 凭证文件路径
CREDENTIALS_DIR="$HOME/projects/rag-course-gen"
CREDENTIALS_FILE="$CREDENTIALS_DIR/.env"

# 提交信息（默认或从参数读取）
COMMIT_MSG="${1:-chore: update codebase}"

echo -e "${GREEN}=== Browsecomp-V3 GitHub 上传脚本 ===${NC}"
echo ""

# 1. 读取GitHub Token
GITHUB_TOKEN=""

# 方法1: 从环境变量读取
if [ -n "$GITHUB_TOKEN" ]; then
    echo -e "${GREEN}✓${NC} 从环境变量读取 GitHub Token"
# 方法2: 从凭证文件读取
elif [ -f "$CREDENTIALS_FILE" ]; then
    GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" "$CREDENTIALS_FILE" 2>/dev/null | cut -d'=' -f2)
    if [ -n "$GITHUB_TOKEN" ]; then
        echo -e "${GREEN}✓${NC} 从凭证文件读取 GitHub Token"
    fi
fi

# 方法3: 提示用户输入
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${YELLOW}未找到 GitHub Token${NC}"
    echo ""
    echo "请选择:"
    echo "  1) 输入 GitHub Token (推荐使用 Personal Access Token)"
    echo "  2) 使用 SSH 密钥 (需要已配置 SSH key)"
    echo -n "选择 [1/2]: "
    read -r choice

    if [ "$choice" = "2" ]; then
        GITHUB_URL="git@github.com:${GITHUB_REPO}.git"
        USE_SSH=true
        echo -e "${GREEN}✓${NC} 使用 SSH 方式"
    else
        echo -n "请输入 GitHub Token: "
        read -rs GITHUB_TOKEN
        echo ""
        if [ -z "$GITHUB_TOKEN" ]; then
            echo -e "${RED}错误: GitHub Token 不能为空${NC}"
            exit 1
        fi

        # 询问是否保存token
        echo -n "是否保存 Token 到凭证文件? [y/N]: "
        read -r save_choice
        if [ "$save_choice" = "y" ] || [ "$save_choice" = "Y" ]; then
            if [ -f "$CREDENTIALS_FILE" ]; then
                # 检查是否已存在GITHUB_TOKEN
                if grep -q "^GITHUB_TOKEN=" "$CREDENTIALS_FILE"; then
                    # 更新现有token
                    sed -i "s/^GITHUB_TOKEN=.*/GITHUB_TOKEN=$GITHUB_TOKEN/" "$CREDENTIALS_FILE"
                else
                    # 添加新token
                    echo "" >> "$CREDENTIALS_FILE"
                    echo "# GitHub Token for code upload" >> "$CREDENTIALS_FILE"
                    echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> "$CREDENTIALS_FILE"
                fi
            else
                mkdir -p "$CREDENTIALS_DIR"
                echo "# GitHub Token for code upload" > "$CREDENTIALS_FILE"
                echo "GITHUB_TOKEN=$GITHUB_TOKEN" >> "$CREDENTIALS_FILE"
            fi
            echo -e "${GREEN}✓${NC} Token 已保存到 $CREDENTIALS_FILE"
        fi
    fi
fi

# 设置远程仓库URL
if [ "$USE_SSH" != "true" ]; then
    GITHUB_URL="https://${GITHUB_TOKEN}@github.com/${GITHUB_REPO}.git"
fi

# 2. 检查远程仓库
echo ""
echo -e "${YELLOW}检查远程仓库...${NC}"
if git remote get-url origin &>/dev/null; then
    CURRENT_URL=$(git remote get-url origin)
    echo -e "${YELLOW}  当前远程: ${CURRENT_URL}${NC}"
    # 更新远程URL
    git remote set-url origin "$GITHUB_URL"
    echo -e "${GREEN}✓${NC} 远程仓库已更新"
else
    git remote add origin "$GITHUB_URL"
    echo -e "${GREEN}✓${NC} 远程仓库已添加"
fi

# 3. 检查git状态
echo ""
echo -e "${YELLOW}检查 Git 状态...${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}  有未提交的更改${NC}"
    git status --short

    # 添加所有更改
    echo ""
    echo -e "${YELLOW}添加更改到暂存区...${NC}"
    git add .

    # 显示暂存的更改
    echo ""
    echo -e "${YELLOW}暂存的更改:${NC}"
    git diff --cached --stat

    # 提交
    echo ""
    echo -e "${YELLOW}提交更改: ${COMMIT_MSG}${NC}"
    git commit -m "$COMMIT_MSG"
    echo -e "${GREEN}✓${NC} 提交完成"
else
    echo -e "${YELLOW}  没有新的更改${NC}"
fi

# 4. 推送到GitHub
echo ""
echo -e "${YELLOW}推送到 GitHub...${NC}"
echo "  仓库: https://github.com/${GITHUB_REPO}"

# 获取当前分支
CURRENT_BRANCH=$(git branch --show-current)

# 检查远程分支是否存在
if git ls-remote --heads origin "$CURRENT_BRANCH" | grep -q "$CURRENT_BRANCH"; then
    echo "  分支: $CURRENT_BRANCH (已存在，将推送新提交)"
else
    echo "  分支: $CURRENT_BRANCH (新分支，将设置上游)"
    UPSTREAM_FLAG="-u"
fi

# 执行推送
if git push ${UPSTREAM_FLAG} origin "$CURRENT_BRANCH"; then
    echo ""
    echo -e "${GREEN}=== 上传成功! ===${NC}"
    echo ""
    echo "仓库地址: https://github.com/${GITHUB_REPO}"
    echo "分支: $CURRENT_BRANCH"
else
    echo ""
    echo -e "${RED}=== 上传失败 ===${NC}"
    echo "请检查:"
    echo "  1. GitHub Token 是否有效"
    echo "  2. 仓库是否存在且你有推送权限"
    echo "  3. 网络连接是否正常"
    exit 1
fi
