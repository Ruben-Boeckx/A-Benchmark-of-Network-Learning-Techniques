import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.nn import SAGEConv, Linear, GATConv

class GraphSAGE(torch.nn.Module):
    def __init__(self, 
                 hidden_dim: int,
                 embedding_dim: int,
                 output_dim: int,
                 num_layers: int,
                 dropout_rate: float,
                 sage_aggr: str):
        super(GraphSAGE, self).__init__()

        self.hidden_dim = hidden_dim
        self.embedding_dim = embedding_dim
        self.output_dim = output_dim
        self.dropout_rate = dropout_rate
        self.dropout = nn.Dropout(dropout_rate)
        self.sage_aggr = sage_aggr
        self.num_layers = num_layers
        self.sage_layers = nn.ModuleList()
        
        if num_layers == 1:
            self.sage1 = SAGEConv((-1, -1), embedding_dim, aggr=sage_aggr)
        else:
            self.sage1 = SAGEConv((-1, -1), hidden_dim, aggr=sage_aggr)
            for _ in range(num_layers - 2):
                self.sage_layers.append(SAGEConv((-1, -1), hidden_dim, aggr=sage_aggr))
            self.sage2 = SAGEConv((-1, -1), embedding_dim, aggr=sage_aggr)

        self.out = Linear(embedding_dim, output_dim)

    def forward(self, x, edge_index):
        h = self.sage1(x, edge_index)
        h = F.relu(h)
        h = self.dropout(h)
        if self.num_layers > 1:
            for layer in self.sage_layers:
                h = layer(h, edge_index)
                h = F.relu(h)
                h = self.dropout(h)
            h = self.sage2(h, edge_index)
        out = self.out(h)
        
        return out

class GAT(torch.nn.Module):
    def __init__(self, 
                 hidden_dim: int,
                 embedding_dim: int,
                 output_dim: int,
                 num_layers: int,
                 dropout_rate: float,
                 heads: int = 1):
        super(GAT, self).__init__()

        self.hidden_dim = hidden_dim
        self.embedding_dim = embedding_dim
        self.output_dim = output_dim
        self.dropout_rate = dropout_rate
        self.dropout = nn.Dropout(dropout_rate)
        self.num_layers = num_layers
        self.heads = heads
        self.gat_layers = nn.ModuleList()
        self.lin_layers = nn.ModuleList()
        
        if num_layers == 1:
            self.gat1 = GATConv((-1, -1), embedding_dim, heads=heads, concat=False, add_self_loops=False)
            self.lin1 = Linear(-1, embedding_dim)
        else:
            self.gat1 = GATConv((-1, -1), hidden_dim, heads=heads, add_self_loops=False)
            self.lin1 = Linear(-1, heads * hidden_dim)
            for _ in range(num_layers - 2):
                self.gat_layers.append(GATConv(heads * hidden_dim, hidden_dim, heads=heads, add_self_loops=False))
                self.lin_layers.append(Linear(heads * hidden_dim, heads * hidden_dim))
            self.gat2 = GATConv(heads * hidden_dim, embedding_dim, heads=heads, concat=False, add_self_loops=False)
            self.lin2 = Linear(heads * hidden_dim, embedding_dim)

        self.out = Linear(embedding_dim, output_dim)

    def forward(self, x, edge_index, edge_attr=None):
        h = self.gat1(x, edge_index, edge_attr=edge_attr) + self.lin1(x)
        h = F.relu(h)
        h = self.dropout(h)
        
        if self.num_layers > 1:
            for gat_layer, lin_layer in zip(self.gat_layers, self.lin_layers):
                h_new = gat_layer(h, edge_index, edge_attr=edge_attr) + lin_layer(h)
                h = F.relu(h_new)
                h = self.dropout(h)
            
            h = self.gat2(h, edge_index, edge_attr=edge_attr) + self.lin2(h)
        
        out = self.out(h)
        
        return out