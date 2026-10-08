#!/usr/bin/env bash
# §7A：禁止 OPS HTTP。白名单目录不在此脚本重复实现，与 Go 测试同一组规则。
set -euo pipefail
cd "$(dirname "$0")/../.."
go test ./internal/architecture -count=1
