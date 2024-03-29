import torch.nn as nn
import torch.nn.functional as F


class Net(nn.Module):
    """Net [Basic conv ne for MNIST Dataset]"""

    def __init__(self, activation=F.relu):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(3, 4, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(4, 12, 5)
        self.fc1 = nn.Linear(12 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 64)
        self.fc3 = nn.Linear(64, 10)

        self.activation = activation

    def forward(self, x, apply_softmax=False):
        x = self.pool(self.activation(self.conv1(x)))
        x = self.pool(self.activation(self.conv2(x)))

        x = x.reshape(-1, 12 * 5 * 5)
        x = self.activation(self.fc1(x))
        x = self.activation(self.fc2(x))
        x = self.fc3(x)
        if apply_softmax:
            x = F.softmax(x, dim=-1)
        return x
