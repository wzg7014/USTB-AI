#!/bin/bash
# AutoDL服务启动脚本 - USTB混合云架构
# 用于训练完成后立即启动RAG和模型推理服务
# 
# 创建时间: 2025-08-06 02:20
# 创建者: 系统集成专家
# 状态: 模型训练期间准备，训练完成后立即执行

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 配置变量
PROJECT_ROOT="/root/autodl-tmp/ustb-project"
RAG_SERVICE_PORT=8000
MODEL_SERVICE_PORT=8001
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/pids"

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p "$LOG_DIR"
    mkdir -p "$PID_DIR"
    mkdir -p "$PROJECT_ROOT/services/rag_system"
    mkdir -p "$PROJECT_ROOT/services/model_inference"
    
    log_success "目录创建完成"
}

# 检查GPU资源状态
check_gpu_status() {
    log_info "检查GPU资源状态..."
    
    # 检查是否有训练进程在运行
    if pgrep -f "deepseek_unsloth_training.py" > /dev/null; then
        log_error "检测到训练进程仍在运行，请等待训练完成"
        log_info "当前运行的训练进程:"
        pgrep -f "deepseek_unsloth_training.py" | xargs ps -p
        return 1
    fi
    
    # 检查GPU状态
    nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
    
    # 检查显存使用情况
    local gpu_memory_used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)
    if [ "$gpu_memory_used" -gt 20000 ]; then
        log_warning "GPU显存使用量较高: ${gpu_memory_used}MB，可能影响服务性能"
    fi
    
    log_success "GPU资源检查完成"
    return 0
}

# 启动RAG服务
start_rag_service() {
    log_info "启动RAG服务 (端口: $RAG_SERVICE_PORT)..."
    
    # 检查端口是否被占用
    if netstat -tuln | grep ":$RAG_SERVICE_PORT " > /dev/null; then
        log_warning "端口 $RAG_SERVICE_PORT 已被占用，尝试停止现有服务"
        pkill -f "rag_gpu_service.py" || true
        sleep 2
    fi
    
    # 切换到RAG服务目录
    cd "$PROJECT_ROOT/services/rag_system"
    
    # 激活conda环境并启动服务
    source /root/miniconda3/etc/profile.d/conda.sh
    conda activate unsloth
    
    # 启动RAG服务
    nohup python rag_gpu_service.py \
        --port $RAG_SERVICE_PORT \
        --gpu-device 0 \
        --batch-size 32 \
        --cache-size 1000 \
        > "$LOG_DIR/rag_service.log" 2>&1 &
    
    local rag_pid=$!
    echo $rag_pid > "$PID_DIR/rag_service.pid"
    
    # 等待服务启动
    log_info "等待RAG服务启动..."
    sleep 10
    
    # 检查服务状态
    if kill -0 $rag_pid 2>/dev/null; then
        # 测试服务健康检查
        if curl -s "http://localhost:$RAG_SERVICE_PORT/health" > /dev/null; then
            log_success "RAG服务启动成功 (PID: $rag_pid)"
            return 0
        else
            log_error "RAG服务启动失败，健康检查不通过"
            return 1
        fi
    else
        log_error "RAG服务进程启动失败"
        return 1
    fi
}

# 启动模型推理服务
start_model_service() {
    log_info "启动模型推理服务 (端口: $MODEL_SERVICE_PORT)..."
    
    # 检查端口是否被占用
    if netstat -tuln | grep ":$MODEL_SERVICE_PORT " > /dev/null; then
        log_warning "端口 $MODEL_SERVICE_PORT 已被占用，尝试停止现有服务"
        pkill -f "model_inference_server.py" || true
        sleep 2
    fi
    
    # 切换到模型推理服务目录
    cd "$PROJECT_ROOT/services/model_inference"
    
    # 激活conda环境
    source /root/miniconda3/etc/profile.d/conda.sh
    conda activate unsloth
    
    # 启动模型推理服务
    nohup python model_inference_server.py \
        --port $MODEL_SERVICE_PORT \
        --model-path "$PROJECT_ROOT/models/trained" \
        --gpu-device 0 \
        --max-length 2048 \
        > "$LOG_DIR/model_service.log" 2>&1 &
    
    local model_pid=$!
    echo $model_pid > "$PID_DIR/model_service.pid"
    
    # 等待服务启动
    log_info "等待模型推理服务启动..."
    sleep 15
    
    # 检查服务状态
    if kill -0 $model_pid 2>/dev/null; then
        # 测试服务健康检查
        if curl -s "http://localhost:$MODEL_SERVICE_PORT/health" > /dev/null; then
            log_success "模型推理服务启动成功 (PID: $model_pid)"
            return 0
        else
            log_error "模型推理服务启动失败，健康检查不通过"
            return 1
        fi
    else
        log_error "模型推理服务进程启动失败"
        return 1
    fi
}

# 性能基准测试
run_performance_test() {
    log_info "运行性能基准测试..."
    
    # 测试RAG服务响应时间
    log_info "测试RAG服务响应时间..."
    local rag_start_time=$(date +%s%3N)
    
    curl -s -X POST "http://localhost:$RAG_SERVICE_PORT/api/v1/search" \
        -H "Content-Type: application/json" \
        -d '{"query": "如何选课", "top_k": 5}' > /dev/null
    
    local rag_end_time=$(date +%s%3N)
    local rag_response_time=$((rag_end_time - rag_start_time))
    
    log_info "RAG服务响应时间: ${rag_response_time}ms"
    
    # 测试模型推理响应时间
    log_info "测试模型推理服务响应时间..."
    local model_start_time=$(date +%s%3N)
    
    curl -s -X POST "http://localhost:$MODEL_SERVICE_PORT/api/v1/inference" \
        -H "Content-Type: application/json" \
        -d '{"query": "如何选课", "max_tokens": 256}' > /dev/null
    
    local model_end_time=$(date +%s%3N)
    local model_response_time=$((model_end_time - model_start_time))
    
    log_info "模型推理响应时间: ${model_response_time}ms"
    
    # 性能评估
    if [ "$rag_response_time" -lt 200 ]; then
        log_success "RAG服务性能达标 (<200ms)"
    else
        log_warning "RAG服务性能未达标 (目标<200ms，实际${rag_response_time}ms)"
    fi
    
    if [ "$model_response_time" -lt 2000 ]; then
        log_success "模型推理性能达标 (<2000ms)"
    else
        log_warning "模型推理性能未达标 (目标<2000ms，实际${model_response_time}ms)"
    fi
}

# 显示服务状态
show_service_status() {
    log_info "服务状态总览:"
    echo "=================================="
    
    # RAG服务状态
    if [ -f "$PID_DIR/rag_service.pid" ]; then
        local rag_pid=$(cat "$PID_DIR/rag_service.pid")
        if kill -0 $rag_pid 2>/dev/null; then
            echo -e "RAG服务:        ${GREEN}运行中${NC} (PID: $rag_pid, 端口: $RAG_SERVICE_PORT)"
        else
            echo -e "RAG服务:        ${RED}已停止${NC}"
        fi
    else
        echo -e "RAG服务:        ${RED}未启动${NC}"
    fi
    
    # 模型推理服务状态
    if [ -f "$PID_DIR/model_service.pid" ]; then
        local model_pid=$(cat "$PID_DIR/model_service.pid")
        if kill -0 $model_pid 2>/dev/null; then
            echo -e "模型推理服务:   ${GREEN}运行中${NC} (PID: $model_pid, 端口: $MODEL_SERVICE_PORT)"
        else
            echo -e "模型推理服务:   ${RED}已停止${NC}"
        fi
    else
        echo -e "模型推理服务:   ${RED}未启动${NC}"
    fi
    
    # GPU状态
    echo ""
    echo "GPU状态:"
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu \
        --format=csv,noheader | while read line; do
        echo "  $line"
    done
    
    echo "=================================="
}

# 停止所有服务
stop_services() {
    log_info "停止所有服务..."
    
    # 停止RAG服务
    if [ -f "$PID_DIR/rag_service.pid" ]; then
        local rag_pid=$(cat "$PID_DIR/rag_service.pid")
        if kill -0 $rag_pid 2>/dev/null; then
            kill $rag_pid
            log_info "RAG服务已停止"
        fi
        rm -f "$PID_DIR/rag_service.pid"
    fi
    
    # 停止模型推理服务
    if [ -f "$PID_DIR/model_service.pid" ]; then
        local model_pid=$(cat "$PID_DIR/model_service.pid")
        if kill -0 $model_pid 2>/dev/null; then
            kill $model_pid
            log_info "模型推理服务已停止"
        fi
        rm -f "$PID_DIR/model_service.pid"
    fi
    
    log_success "所有服务已停止"
}

# 主函数
main() {
    log_info "开始启动AutoDL混合云服务..."
    log_info "项目根目录: $PROJECT_ROOT"
    
    case "${1:-start}" in
        "start")
            create_directories
            
            if ! check_gpu_status; then
                log_error "GPU状态检查失败，退出启动流程"
                exit 1
            fi
            
            if start_rag_service && start_model_service; then
                log_success "所有服务启动成功！"
                
                # 运行性能测试
                sleep 5
                run_performance_test
                
                # 显示服务状态
                show_service_status
                
                log_info "AutoDL混合云架构部署完成！"
                log_info "RAG服务: http://localhost:$RAG_SERVICE_PORT"
                log_info "模型推理服务: http://localhost:$MODEL_SERVICE_PORT"
                
            else
                log_error "服务启动失败"
                stop_services
                exit 1
            fi
            ;;
            
        "stop")
            stop_services
            ;;
            
        "status")
            show_service_status
            ;;
            
        "restart")
            stop_services
            sleep 3
            main start
            ;;
            
        *)
            echo "用法: $0 {start|stop|status|restart}"
            echo "  start   - 启动所有服务"
            echo "  stop    - 停止所有服务"
            echo "  status  - 显示服务状态"
            echo "  restart - 重启所有服务"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
