import csv
import heapq
import re
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

BASE_DIR = Path(__file__).parent
SUBWAY_CSV = BASE_DIR / "subway.csv"
LOCATION_CSV = BASE_DIR / "subwayLocation.csv"

LINE_COLORS = {
    "1": "#0052A4",
    "2": "#00A84D",
    "3": "#EF7C1C",
    "4": "#00A5DE",
    "5": "#996CAC",
    "6": "#CD7C2F",
    "7": "#747F00",
    "8": "#E6186C",
    "9": "#BDB092",
}


def strip_line(node: str) -> str:
    return re.sub(r"\(\d+\)$", "", node).strip()


def line_of(node: str) -> str:
    m = re.search(r"\((\d+)\)$", node)
    return m.group(1) if m else ""


@st.cache_data
def load_graph():
    graph: dict[str, list[tuple[str, float]]] = {}
    edges: list[tuple[str, str, float]] = []
    with SUBWAY_CSV.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            u, v, w = row[0].strip(), row[1].strip(), float(row[2])
            graph.setdefault(u, []).append((v, w))
            graph.setdefault(v, []).append((u, w))
            edges.append((u, v, w))
    return graph, edges


@st.cache_data
def load_locations():
    loc: dict[str, tuple[float, float]] = {}
    with LOCATION_CSV.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 3:
                continue
            name = row[0].strip()
            try:
                lat, lon = float(row[1]), float(row[2])
            except ValueError:
                continue
            loc.setdefault(name, (lat, lon))
    return loc


def dijkstra(graph, start, goal):
    if start not in graph or goal not in graph:
        return None, float("inf")
    dist = {start: 0.0}
    prev: dict[str, str] = {}
    pq: list[tuple[float, str]] = [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            break
        if d > dist.get(u, float("inf")):
            continue
        for v, w in graph[u]:
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if goal not in dist:
        return None, float("inf")
    path = [goal]
    while path[-1] != start:
        path.append(prev[path[-1]])
    return list(reversed(path)), dist[goal]


def main():
    st.set_page_config(page_title="지하철 최단경로", layout="wide")
    st.title("지하철 최단 경로 찾기")
    st.caption("subway.csv의 역 간 시간을 가중치로 다익스트라 알고리즘을 적용해 최단 경로를 찾고 지도에 표시합니다.")

    graph, edges = load_graph()
    locations = load_locations()
    stations = sorted(graph.keys())

    col1, col2 = st.columns(2)
    with col1:
        default_start_idx = stations.index("서울역(1)") if "서울역(1)" in stations else 0
        start = st.selectbox("출발역", stations, index=default_start_idx)
    with col2:
        default_goal = "잠실(2)" if "잠실(2)" in stations else stations[-1]
        goal = st.selectbox("도착역", stations, index=stations.index(default_goal))

    if st.button("최단 경로 찾기", type="primary"):
        path, total = dijkstra(graph, start, goal)
        if path is None:
            st.error("두 역 사이에 경로가 없습니다.")
            return

        st.success(f"총 소요 시간: 약 **{total:.0f}분**, 경유 역 수: **{len(path)}개**")
        st.write(" → ".join(path))

        coords = [locations.get(strip_line(n)) for n in path]
        valid_coords = [c for c in coords if c is not None]
        if not valid_coords:
            st.warning("경로상의 역 좌표를 찾을 수 없습니다.")
            return

        center_lat = sum(c[0] for c in valid_coords) / len(valid_coords)
        center_lon = sum(c[1] for c in valid_coords) / len(valid_coords)
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="CartoDB positron")

        for u, v, _ in edges:
            cu = locations.get(strip_line(u))
            cv = locations.get(strip_line(v))
            if cu is None or cv is None:
                continue
            lu, lv = line_of(u), line_of(v)
            if lu == lv:
                color = LINE_COLORS.get(lu, "#AAAAAA")
                folium.PolyLine([cu, cv], color=color, weight=2, opacity=0.4).add_to(m)

        for i in range(len(path) - 1):
            cu = locations.get(strip_line(path[i]))
            cv = locations.get(strip_line(path[i + 1]))
            if cu is None or cv is None:
                continue
            folium.PolyLine([cu, cv], color="red", weight=6, opacity=0.9).add_to(m)

        for i, node in enumerate(path):
            c = locations.get(strip_line(node))
            if c is None:
                continue
            if i == 0:
                icon = folium.Icon(color="green", icon="play", prefix="fa")
                tag = f"출발: {node}"
            elif i == len(path) - 1:
                icon = folium.Icon(color="red", icon="flag", prefix="fa")
                tag = f"도착: {node}"
            else:
                icon = folium.Icon(color="blue", icon="subway", prefix="fa")
                tag = node
            folium.Marker(c, tooltip=tag, popup=tag, icon=icon).add_to(m)

        st_folium(m, width=None, height=650, returned_objects=[])
    else:
        st.info("출발역과 도착역을 선택한 뒤 버튼을 누르세요.")


if __name__ == "__main__":
    main()
