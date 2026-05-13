"""Industry chain analysis — supply chain positioning for investment decisions.

Provides:
  - Industry composition (peers in same sector)
  - Upstream/downstream identification based on sector classification
  - Complementary and substitute product sectors
  - Industry concentration and competitive landscape

Uses akshare stock_board_industry_* APIs + East Money datacenter.
Disk cache at .hermes/cache/industry_chain.json with 4-hour TTL.
"""

import time
import logging
from hermes.api.eastmoney import em_get
from hermes.config import CONFIG_DIR
from hermes.data.cache import DiskCache

log = logging.getLogger(__name__)

_cache = DiskCache(CONFIG_DIR / "cache", "industry_chain.json", ttl=4 * 3600)

# Industry chain mapping: key sectors → their upstream/downstream/complementary/substitute
_CHAIN_MAP = {
    "消费电子": {
        "upstream": ["半导体", "电子元件", "光学光电", "印制电路板"],
        "downstream": ["智能手机", "可穿戴设备", "VR/AR", "汽车电子"],
        "complementary": ["软件开发", "通信设备", "电池"],
        "substitute": ["传统家电", "功能手机"],
    },
    "半导体": {
        "upstream": ["电子化学品", "硅片", "光刻胶"],
        "downstream": ["消费电子", "汽车电子", "通信设备", "计算机"],
        "complementary": ["封装测试", "EDA软件"],
        "substitute": [],
    },
    "新能源汽车": {
        "upstream": ["锂电池", "稀土", "汽车零部件"],
        "downstream": ["充电桩", "汽车服务", "保险"],
        "complementary": ["智能驾驶", "车联网"],
        "substitute": ["传统汽车", "公共交通"],
    },
    "医药": {
        "upstream": ["化学原料药", "中药", "医疗器械"],
        "downstream": ["医院", "药店", "健康服务"],
        "complementary": ["保险", "健康管理"],
        "substitute": ["保健品", "传统疗法"],
    },
    "白酒": {
        "upstream": ["粮食", "包装"],
        "downstream": ["餐饮", "零售", "电商"],
        "complementary": ["酒店", "旅游"],
        "substitute": ["啤酒", "红酒", "其他酒类"],
    },
    "银行": {
        "upstream": [],
        "downstream": ["房地产", "基建", "制造业"],
        "complementary": ["保险", "证券", "支付"],
        "substitute": ["互联网金融", "信托"],
    },
    "房地产": {
        "upstream": ["建材", "钢铁", "家电"],
        "downstream": ["物业管理", "装修", "家具"],
        "complementary": ["银行", "保险"],
        "substitute": ["租房", "长租公寓"],
    },
    "计算机": {
        "upstream": ["半导体", "电子元件", "显示器"],
        "downstream": ["软件开发", "云服务", "企业服务"],
        "complementary": ["网络安全", "数据中心"],
        "substitute": ["平板", "手机"],
    },
    "电力设备": {
        "upstream": ["铜", "铝", "钢铁", "绝缘材料"],
        "downstream": ["电网", "新能源发电", "工业"],
        "complementary": ["储能", "智能电网"],
        "substitute": [],
    },
    "食品": {
        "upstream": ["农业", "养殖", "包装"],
        "downstream": ["零售", "餐饮", "电商"],
        "complementary": ["冷链物流"],
        "substitute": ["进口食品"],
    },
    "物流": {
        "upstream": ["仓储", "包装", "运输设备"],
        "downstream": ["电商", "制造业", "零售"],
        "complementary": ["供应链管理", "跨境贸易"],
        "substitute": ["自建物流", "直营配送"],
    },
    "通信": {
        "upstream": ["半导体", "光纤光缆", "电子元件"],
        "downstream": ["运营商", "互联网服务", "企业通信"],
        "complementary": ["网络安全", "云计算"],
        "substitute": ["卫星通信"],
    },
    "钢铁": {
        "upstream": ["铁矿石", "焦炭", "废钢"],
        "downstream": ["房地产", "汽车", "基建", "机械"],
        "complementary": ["合金材料", "表面处理"],
        "substitute": ["铝材", "复合材料"],
    },
    "煤炭": {
        "upstream": ["采矿设备", "爆破器材"],
        "downstream": ["电力", "钢铁", "化工", "建材"],
        "complementary": ["铁路运输", "港口"],
        "substitute": ["天然气", "新能源发电"],
    },
    "石油石化": {
        "upstream": ["油气开采", "钻井设备"],
        "downstream": ["化工", "塑料", "橡胶", "燃料"],
        "complementary": ["管道运输", "仓储"],
        "substitute": ["新能源", "生物燃料"],
    },
    "军工": {
        "upstream": ["特种材料", "电子元件", "精密加工"],
        "downstream": ["国防", "航空航天", "民用转化"],
        "complementary": ["通信", "导航", "网络安全"],
        "substitute": [],
    },
    "保险": {
        "upstream": ["银行", "证券"],
        "downstream": ["个人保障", "企业风控", "再保险"],
        "complementary": ["健康管理", "养老服务"],
        "substitute": ["自保", "互助"],
    },
    "证券": {
        "upstream": ["银行", "数据服务"],
        "downstream": ["投资管理", "融资", "并购"],
        "complementary": ["金融科技", "监管服务"],
        "substitute": ["银行理财", "基金"],
    },
    "家电": {
        "upstream": ["半导体", "电子元件", "塑料", "压缩机"],
        "downstream": ["零售", "电商", "房地产"],
        "complementary": ["智能家居", "售后服务"],
        "substitute": ["商用设备"],
    },
    "纺织服装": {
        "upstream": ["棉花", "化纤", "染料"],
        "downstream": ["零售", "电商", "品牌运营"],
        "complementary": ["物流", "包装"],
        "substitute": ["进口品牌", "快时尚"],
    },
    "建材": {
        "upstream": ["水泥", "玻璃", "陶瓷原料"],
        "downstream": ["房地产", "基建", "装修"],
        "complementary": ["设计服务", "施工"],
        "substitute": ["新型材料", "钢结构"],
    },
    "农业": {
        "upstream": ["种子", "化肥", "农药", "农机"],
        "downstream": ["食品加工", "餐饮", "零售"],
        "complementary": ["冷链物流", "期货"],
        "substitute": ["进口农产品"],
    },
    "传媒": {
        "upstream": ["内容制作", "技术平台"],
        "downstream": ["广告", "流媒体", "出版"],
        "complementary": ["通信", "互联网"],
        "substitute": ["游戏", "社交平台"],
    },
    "环保": {
        "upstream": ["环保设备", "监测仪器"],
        "downstream": ["市政", "工业", "能源"],
        "complementary": ["新能源", "循环经济"],
        "substitute": [],
    },
}

# Fallback: generic mapping for industries not in _CHAIN_MAP
_GENERIC_CHAIN = {
    "upstream": ["原材料", "零部件"],
    "downstream": ["终端应用", "服务"],
    "complementary": ["配套服务"],
    "substitute": ["替代产品"],
}


def _fetch_industry_composition(industry: str) -> list[dict] | None:
    """Fetch peer companies in the same industry sector via akshare."""
    try:
        import akshare as ak
        df = ak.stock_board_industry_cons_em(symbol=industry)
        if df is None or len(df) == 0:
            return None
        peers = []
        for _, row in df.iterrows():
            try:
                peers.append({
                    "code": str(row.get("代码", "")),
                    "name": str(row.get("名称", "")),
                    "price": float(row.get("最新价", 0)) if row.get("最新价") else None,
                    "change_pct": float(row.get("涨跌幅", 0)) if row.get("涨跌幅") else None,
                    "market_cap": float(row.get("总市值", 0)) if row.get("总市值") else None,
                    "pe": float(row.get("PE(TTM)", 0)) if row.get("PE(TTM)", "-") != "-" else None,
                })
            except (ValueError, TypeError):
                continue
        return peers if peers else None
    except Exception as e:
        log.warning(f"akshare industry composition failed for {industry}: {e}")
        return None


def _fetch_from_push2(industry: str) -> list[dict] | None:
    """Fallback: fetch peer companies via push2 clist API."""
    url = (
        f"http://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fltt=2"
        f"&invt=2&fs=m:1+t:2,m:0+t:6,m:0+t:80,m:1+t:23"
        f"&fields=f2,f3,f9,f12,f14,f20,f23,f100,f115,f169,f170"
    )
    data = em_get(url, timeout=20)
    if not data or not data.get("data") or not data["data"].get("diff"):
        return None

    peers = []
    for item in data["data"]["diff"]:
        if item.get("f100") == industry:
            try:
                peers.append({
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "price": float(item.get("f2", 0)) if item.get("f2") != "-" else None,
                    "change_pct": float(item.get("f3", 0)) if item.get("f3") != "-" else None,
                    "pe": float(item.get("f9", 0)) if item.get("f9") != "-" else None,
                    "pb": float(item.get("f23", 0)) if item.get("f23") != "-" else None,
                    "market_cap": float(item.get("f20", 0)) if item.get("f20") != "-" else None,
                    "profit_yoy": float(item.get("f115", 0)) if item.get("f115") != "-" else None,
                    "revenue_yoy": float(item.get("f170", 0)) if item.get("f170") != "-" else None,
                })
            except (ValueError, TypeError):
                continue
    return peers if peers else None


def industry_chain(code: str) -> dict:
    """Get industry chain analysis for a stock.

    Returns supply chain positioning (upstream/downstream/complementary/substitute),
    peer companies in the same sector, and competitive landscape summary.
    """
    from hermes.data.quote import stock_quote

    quote = stock_quote(code)
    if "error" in quote:
        return {"error": "Failed to get quote for industry identification", "code": code}

    industry = quote.get("industry", "")
    if not industry:
        return {"error": "Industry identification unavailable", "code": code}

    # Chain position from mapping
    chain = _CHAIN_MAP.get(industry, _GENERIC_CHAIN)

    # Peer composition
    cached = _cache.load()
    peers_key = f"peers_{industry}"
    peers = None
    if cached and peers_key in cached:
        peers = cached[peers_key]

    if peers is None:
        peers = _fetch_industry_composition(industry)
        if peers is None:
            peers = _fetch_from_push2(industry)
        if peers:
            if cached is None:
                cached = {}
            cached[peers_key] = peers
            _cache.save(cached)

    # Competitive landscape summary
    total_peers = len(peers) if peers else 0
    if peers and total_peers >= 3:
        mcap_list = sorted([p.get("market_cap", 0) or 0 for p in peers], reverse=True)
        top3_share = sum(mcap_list[:3]) / sum(mcap_list) if sum(mcap_list) > 0 else None
        our_mcap = quote.get("market_cap", 0)
        our_rank = sum(1 for p in peers if (p.get("market_cap") or 0) > our_mcap) + 1
        landscape = {
            "total_peers": total_peers,
            "top3_concentration": round(top3_share, 2) if top3_share else None,
            "our_market_cap_rank": our_rank,
            "our_market_cap": our_mcap,
        }
    else:
        landscape = {"total_peers": total_peers}

    # Top 10 peers by market cap
    top_peers = sorted(peers or [], key=lambda x: x.get("market_cap", 0) or 0, reverse=True)[:10]

    return {
        "code": code,
        "name": quote.get("name", ""),
        "industry": industry,
        "chain_position": chain,
        "peers": top_peers,
        "landscape": landscape,
        "source": "akshare+push2" if peers else "mapping_only",
    }