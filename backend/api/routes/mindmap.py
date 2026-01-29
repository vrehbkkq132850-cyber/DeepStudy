"""
思维导图相关路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from backend.api.schemas.response import MindMapGraph
from backend.api.middleware.auth import get_current_user_id
from backend.data.neo4j_client import neo4j_client
import uuid
import logging

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mindmap", tags=["mindmap"])


def generate_mind_map_from_triples(triples):
    """
    从知识三元组生成思维导图数据
    构建层次化的知识结构，使用智能布局算法
    
    Args:
        triples: 知识三元组列表
        
    Returns:
        MindMapGraph 格式的数据
    """
    nodes = []
    edges = []
    node_id_map = {}
    
    # 生成中心节点
    center_node_id = f"node_{uuid.uuid4()[:8]}"
    nodes.append({
        "id": center_node_id,
        "data": {
            "label": "知识中心",
            "type": "center"
        },
        "position": {"x": 400, "y": 100},
        "style": {
            "background": "#007bff",
            "color": "white",
            "borderRadius": "8px",
            "padding": "12px",
            "fontWeight": "bold"
        }
    })
    
    # 分析三元组，构建层次结构
    # 1. 找出核心概念（出现频率最高的主语）
    subject_freq = {}
    for triple in triples:
        subject_freq[triple['subject']] = subject_freq.get(triple['subject'], 0) + 1
    
    # 按频率排序，找出核心概念
    sorted_subjects = sorted(subject_freq.items(), key=lambda x: x[1], reverse=True)
    core_concepts = [subject for subject, _ in sorted_subjects[:3]]  # 前3个核心概念
    
    # 2. 构建层次结构
    # 第一层：核心概念（中心节点的直接子节点）
    # 第二层：与核心概念相关的概念
    # 第三层：具体应用和例子
    
    # 生成核心概念节点（第一层）
    core_nodes = []
    core_positions = [
        {"x": 200, "y": 250},  # 左上
        {"x": 400, "y": 250},  # 正下
        {"x": 600, "y": 250}   # 右上
    ]
    
    for i, core_concept in enumerate(core_concepts[:3]):
        if core_concept not in node_id_map:
            core_node_id = f"node_{uuid.uuid4()[:8]}"
            node_id_map[core_concept] = core_node_id
            nodes.append({
                "id": core_node_id,
                "data": {
                    "label": core_concept,
                    "type": "core"
                },
                "position": core_positions[i],
                "style": {
                    "background": "#e3f2fd",
                    "border": "2px solid #2196f3",
                    "borderRadius": "8px",
                    "padding": "10px",
                    "fontWeight": "600"
                }
            })
            core_nodes.append(core_node_id)
            
            # 连接中心节点到核心概念
            edge_id = f"edge_{uuid.uuid4()[:8]}"
            edges.append({
                "id": edge_id,
                "source": center_node_id,
                "target": core_node_id,
                "style": {
                    "stroke": "#007bff",
                    "strokeWidth": 2
                }
            })
    
    # 处理其他三元组，构建层次结构
    # 为每个核心概念分配相关的三元组
    concept_relations = {}
    for core in core_concepts:
        concept_relations[core] = []
    
    # 分配三元组到核心概念
    for triple in triples:
        # 找到最相关的核心概念
        best_core = None
        max_relevance = 0
        
        for core in core_concepts:
            relevance = 0
            if triple['subject'] == core or triple['object'] == core:
                relevance = 2
            elif core in triple['subject'] or core in triple['object']:
                relevance = 1
            
            if relevance > max_relevance:
                max_relevance = relevance
                best_core = core
        
        if best_core:
            concept_relations[best_core].append(triple)
    
    # 为每个核心概念生成子节点（第二层和第三层）
    level_offset = 150  # 每层的垂直偏移
    sibling_offset = 100  # 兄弟节点的水平偏移
    
    for core_idx, (core_concept, related_triples) in enumerate(concept_relations.items()):
        core_node_id = node_id_map.get(core_concept)
        if not core_node_id:
            continue
        
        # 获取核心节点位置
        core_position = core_positions[core_idx]
        
        # 处理与核心概念相关的三元组
        child_nodes = []
        for triple_idx, triple in enumerate(related_triples):
            # 生成宾语节点（第二层）
            if triple['object'] not in node_id_map:
                child_node_id = f"node_{uuid.uuid4()[:8]}"
                node_id_map[triple['object']] = child_node_id
                
                # 计算位置：基于核心节点的位置
                x = core_position['x'] + (triple_idx - len(related_triples)/2) * sibling_offset
                y = core_position['y'] + level_offset
                
                nodes.append({
                    "id": child_node_id,
                    "data": {
                        "label": triple['object'],
                        "type": "concept"
                    },
                    "position": {"x": x, "y": y},
                    "style": {
                        "background": "#fff3e0",
                        "border": "2px solid #ff9800",
                        "borderRadius": "8px",
                        "padding": "8px"
                    }
                })
                child_nodes.append(child_node_id)
            else:
                child_node_id = node_id_map[triple['object']]
            
            # 生成边（核心概念 -> 子概念）
            edge_id = f"edge_{uuid.uuid4()[:8]}"
            edges.append({
                "id": edge_id,
                "source": core_node_id,
                "target": child_node_id,
                "label": triple['relation'],
                "style": {
                    "stroke": "#6c757d",
                    "strokeWidth": 2
                },
                "labelStyle": {
                    "background": "white",
                    "padding": "4px 8px",
                    "borderRadius": "4px",
                    "fontSize": "12px"
                }
            })
    
    # 3. 优化布局，避免节点重叠
    # 简单的碰撞检测和调整
    for i, node1 in enumerate(nodes):
        for j, node2 in enumerate(nodes):
            if i != j:
                pos1 = node1['position']
                pos2 = node2['position']
                # 计算距离
                distance = ((pos1['x'] - pos2['x']) ** 2 + (pos1['y'] - pos2['y']) ** 2) ** 0.5
                # 如果距离太近，调整位置
                if distance < 80:
                    # 向相反方向移动
                    dx = pos1['x'] - pos2['x']
                    dy = pos1['y'] - pos2['y']
                    if dx == 0:
                        dx = 1
                    if dy == 0:
                        dy = 1
                    # 计算单位向量
                    length = (dx ** 2 + dy ** 2) ** 0.5
                    dx_normalized = dx / length
                    dy_normalized = dy / length
                    # 移动节点
                    node2['position']['x'] += dx_normalized * 20
                    node2['position']['y'] += dy_normalized * 20
    
    return MindMapGraph(nodes=nodes, edges=edges)


def generate_default_mind_map():
    """
    生成默认的思维导图数据
    
    Returns:
        MindMapGraph 格式的数据
    """
    nodes = [
        {
            "id": "node1",
            "data": {
                "label": "知识中心",
                "type": "center"
            },
            "position": {"x": 400, "y": 200},
            "style": {
                "background": "#007bff",
                "color": "white",
                "borderRadius": "8px",
                "padding": "12px",
                "fontWeight": "bold"
            }
        },
        {
            "id": "node2",
            "data": {
                "label": "概念",
                "type": "concept"
            },
            "position": {"x": 200, "y": 100},
            "style": {
                "background": "#fff",
                "border": "2px solid #28a745",
                "borderRadius": "8px",
                "padding": "10px"
            }
        },
        {
            "id": "node3",
            "data": {
                "label": "应用",
                "type": "application"
            },
            "position": {"x": 600, "y": 100},
            "style": {
                "background": "#fff",
                "border": "2px solid #ffc107",
                "borderRadius": "8px",
                "padding": "10px"
            }
        },
        {
            "id": "node4",
            "data": {
                "label": "例子",
                "type": "example"
            },
            "position": {"x": 400, "y": 350},
            "style": {
                "background": "#fff",
                "border": "2px solid #dc3545",
                "borderRadius": "8px",
                "padding": "10px"
            }
        }
    ]
    
    edges = [
        {
            "id": "edge1",
            "source": "node1",
            "target": "node2",
            "label": "包含",
            "style": {
                "stroke": "#007bff",
                "strokeWidth": 2
            }
        },
        {
            "id": "edge2",
            "source": "node1",
            "target": "node3",
            "label": "应用于",
            "style": {
                "stroke": "#007bff",
                "strokeWidth": 2
            }
        },
        {
            "id": "edge3",
            "source": "node1",
            "target": "node4",
            "label": "示例",
            "style": {
                "stroke": "#007bff",
                "strokeWidth": 2
            }
        }
    ]
    
    return MindMapGraph(nodes=nodes, edges=edges)


@router.get("/{conversation_id}", response_model=MindMapGraph)
async def get_mind_map(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    获取思维导图数据
    
    Args:
        conversation_id: 对话 ID
        user_id: 当前用户 ID
        
    Returns:
        思维导图数据
    """
    try:
        logger.info(f"生成知识图谱，conversation_id={conversation_id}")
        
        # 从 Neo4j 获取对话节点
        dialogue_node = await neo4j_client.get_dialogue_node(conversation_id)
        
        # 这里模拟从对话内容中提取知识三元组
        # 实际应用中，应该从对话节点的 content 或相关的知识三元组存储中获取
        # 为了演示，我们生成一些示例三元组
        example_triples = [
            {"subject": "人工智能", "relation": "是", "object": "研究智能的科学"},
            {"subject": "机器学习", "relation": "属于", "object": "人工智能"},
            {"subject": "深度学习", "relation": "属于", "object": "机器学习"},
            {"subject": "神经网络", "relation": "是", "object": "深度学习的基础"},
            {"subject": "人工智能", "relation": "应用于", "object": "计算机视觉"}
        ]
        
        # 如果有真实的对话内容，可以基于内容生成三元组
        if dialogue_node and dialogue_node.get('content'):
            content = dialogue_node['content']
            logger.info(f"从对话内容生成知识图谱，内容长度: {len(content)}")
            # 这里可以调用知识提取器生成三元组
            # 暂时使用示例三元组
            triples = example_triples
        else:
            logger.info("使用默认知识图谱")
            triples = example_triples
        
        # 生成知识图谱
        if triples:
            mind_map = generate_mind_map_from_triples(triples)
            logger.info(f"成功生成知识图谱，节点数: {len(mind_map.nodes)}, 边数: {len(mind_map.edges)}")
        else:
            mind_map = generate_default_mind_map()
            logger.info("生成默认知识图谱")
        
        return mind_map
        
    except Exception as e:
        logger.error(f"生成知识图谱失败: {str(e)}")
        # 失败时返回默认知识图谱
        return generate_default_mind_map()
