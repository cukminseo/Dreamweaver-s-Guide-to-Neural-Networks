import torch
import torch.nn as nn


# Swish activation function
class Swish(nn.Module):
    def forward(self, x):
        return x * torch.sigmoid(x)


# Squeeze-and-excitation module
class SEBlock(nn.Module):
    def __init__(self, in_channels, se_ratio=4):
        super(SEBlock, self).__init__()
        self.se_reduce = nn.Conv2d(in_channels, in_channels // se_ratio, kernel_size=1, stride=1, padding=0, bias=True)
        self.se_expand = nn.Conv2d(in_channels // se_ratio, in_channels, kernel_size=1, stride=1, padding=0, bias=True)

    def forward(self, x):
        se_tensor = torch.nn.functional.adaptive_avg_pool2d(x, (1, 1))
        se_tensor = self.se_expand(torch.relu(self.se_reduce(se_tensor)))
        return torch.sigmoid(se_tensor) * x


# Mobile inverted bottleneck block (MBConv)
class MBConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, expand_ratio, se_ratio):
        super(MBConv, self).__init__()
        self.stride = stride
        self.expand = in_channels != out_channels
        hidden_dim = in_channels * expand_ratio
        self.use_res_connect = self.stride == 1 and in_channels == out_channels

        layers = []
        # Expansion phase
        if expand_ratio != 1:
            layers += [
                nn.Conv2d(in_channels, hidden_dim, kernel_size=1, stride=1, padding=0, bias=False),
                nn.BatchNorm2d(hidden_dim),
                Swish(),
                # LeakyReLU()
            ]
        # Depthwise convolution phase
        layers += [
            nn.Conv2d(hidden_dim, hidden_dim, kernel_size, stride, padding=kernel_size // 2, groups=hidden_dim,
                      bias=False),
            nn.BatchNorm2d(hidden_dim),
            Swish(),
            # LeakyReLU()
        ]
        # Squeeze-and-excitation phase
        layers += [SEBlock(hidden_dim, se_ratio)]
        # Output phase
        layers += [
            nn.Conv2d(hidden_dim, out_channels, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(out_channels)
        ]
        self.block = nn.Sequential(*layers)

        # Xavier initialization
        for m in self.block.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.xavier_uniform_(m.weight)

    def forward(self, x):
        if self.use_res_connect:
            return x + self.block(x)
        return self.block(x)


# Swish 대신 LeakyReLU 사용
class LeakyReLU(nn.Module):
    def forward(self, x):
        return nn.functional.leaky_relu(x, negative_slope=0.01)


# EfficientNet model
class EfficientNet(nn.Module):
    # # 가중치 초기화
    # def initialize_weights(self, m):
    #     if isinstance(m, nn.Conv2d) or isinstance(m, nn.Linear):
    #         nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
    #         if m.bias is not None:
    #             nn.init.constant_
    def __init__(self, num_class=30):
        super(EfficientNet, self).__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            Swish(),
            # LeakyReLU()
        )
        self.dropout = nn.Dropout(p=0.6)  # Dropout 추가
        # Xavier initialization
        nn.init.xavier_uniform_(self.stem[0].weight)


        # Define MBConv blocks
        self.blocks = nn.Sequential(
            MBConv(32, 16, 3, 1, 1, 4),
            MBConv(16, 24, 3, 2, 6, 4),
            MBConv(24, 24, 3, 1, 6, 4),
            MBConv(24, 40, 5, 2, 6, 4),
            MBConv(40, 40, 5, 1, 6, 4),
            MBConv(40, 80, 3, 2, 6, 4),
            MBConv(80, 80, 3, 1, 6, 4),
            MBConv(80, 80, 3, 1, 6, 4),
            MBConv(80, 112, 5, 1, 6, 4),
            MBConv(112, 112, 5, 1, 6, 4),
            MBConv(112, 192, 5, 2, 6, 4),
            MBConv(192, 192, 5, 1, 6, 4),
            MBConv(192, 192, 5, 1, 6, 4),
            MBConv(192, 320, 3, 1, 6, 4)
        )
        self.head = nn.Sequential(
            nn.Conv2d(320, 1280, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(1280),
            Swish(),
            # LeakyReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            # nn.Dropout(0.5),
            nn.Linear(1280, num_class)
        )
        # # Xavier initialization
        # nn.init.xavier_uniform_(self.head[0].weight)
        # nn.init.xavier_uniform_(self.head[6].weight)
        # Apply weight initialization
        self.apply(self.initialize_weights)

    def forward(self, x):
        x = self.stem(x)
        x = self.blocks(x)
        x = self.dropout(x)  # Dropout 적용
        x = self.head(x)
        return x

    def initialize_weights(self, m):
        if isinstance(m, nn.Conv2d):
            nn.init.xavier_uniform_(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.Linear):
            nn.init.xavier_uniform_(m.weight)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)


# Create EfficientNet model
# model = EfficientNet()
