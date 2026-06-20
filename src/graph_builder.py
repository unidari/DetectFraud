# -*- coding: utf-8 -*-
import pandas as pd
import plotly.graph_objects as go
import networkx as nx

class GraphBuilder:
    @staticmethod
    def build_interactive_graph(df, weight_by='summa', max_edges=100):
        # --- ГАРАНТИРУЕМ НАЛИЧИЕ СЛУЖЕБНЫХ КОЛОНОК ---
        if 'счет_дебет' not in df.columns:
            df['счет_дебет'] = df['дебет'].astype(str).str.split('.').str[0]
        if 'счет_кредит' not in df.columns:
            df['счет_кредит'] = df['кредит'].astype(str).str.split('.').str[0]
        # -----------------------------------------------

        if weight_by == 'summa':
            agg = df.groupby(['счет_дебет', 'счет_кредит'])['сумма'].sum().reset_index()
            agg = agg.sort_values('сумма', ascending=False).head(max_edges)
            edge_weight = agg['сумма'].values
        else:
            agg = df.groupby(['счет_дебет', 'счет_кредит']).size().reset_index(name='freq')
            agg = agg.sort_values('freq', ascending=False).head(max_edges)
            edge_weight = agg['freq'].values

        G = nx.DiGraph()
        for _, row in agg.iterrows():
            src = str(row['счет_дебет'])
            dst = str(row['счет_кредит'])
            w = row['сумма'] if weight_by == 'summa' else row['freq']
            G.add_edge(src, dst, weight=w)

        pos = nx.spring_layout(G, seed=42, k=2)

        node_x, node_y, node_text = [], [], []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)

        edge_x, edge_y = [], []
        for src, dst in G.edges():
            x0, y0 = pos[src]
            x1, y1 = pos[dst]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="top center",
            hoverinfo='text',
            marker=dict(size=20, color='lightblue', line=dict(width=2, color='DarkSlateGrey'))
        )
        fig = go.Figure(data=[edge_trace, node_trace],
                        layout=go.Layout(
                            title='Граф связей счетов',
                            showlegend=False,
                            hovermode='closest',
                            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                            width=800, height=600
                        ))
        return fig