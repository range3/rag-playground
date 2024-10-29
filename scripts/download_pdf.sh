#!/bin/bash
set -eu

# 定義部分
ROOT_DIR=$(cd $(dirname $0)/..; pwd)
DST_DIR="${ROOT_DIR}/data/proceedings"

# ディレクトリを作成
mkdir -p "${DST_DIR}"

# rsyncコマンドでPDFファイルをダウンロード
cmd_rsync=(
  rsync
  -avz
  --progress
  --include "*/"
  --include "*.pdf"
  --exclude "*"
  --prune-empty-dirs
  --ignore-errors
  work:/home/proceedings/ 
  "${DST_DIR}/"
)

echo "Downloading PDF files with rsync..."
echo "${cmd_rsync[@]}"
"${cmd_rsync[@]}" || true
