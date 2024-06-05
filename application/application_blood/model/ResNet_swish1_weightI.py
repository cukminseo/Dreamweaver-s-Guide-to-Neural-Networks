import torch
import torch.nn as nn
import torch.nn.init as init  # <-- Add this line

class Swish(nn.Module):
    def forward(self, x):
        return x * torch.sigmoid(x)

class ResNet(nn.Module):
    def __init__(self, block, layers, num_class=30):
        super(ResNet, self).__init__()
        self.inplanes = 64
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3),  # in_channel 3에서 1로 수정
            nn.BatchNorm2d(64),
            Swish()
        )
        # Xavier initialization
        init.xavier_uniform_(self.conv1[0].weight)

        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer0 = self._make_layer(block, 64, layers[0], stride=1)
        self.layer1 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer2 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer3 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d(3)
        self.fc = nn.Linear(512, num_class)
        self.dropout = nn.Dropout(p=0.5)  # Dropout layer 추가


        # Xavier initialization
        init.xavier_uniform_(self.fc.weight)

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes, kernel_size=1, stride=stride),
                nn.BatchNorm2d(planes),
            )
        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.maxpool(x)
        x = self.layer0(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.dropout(x)  # Dropout 적용
        x = self.fc(x)

        return x


class ResidualBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, downsample=None):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1),
            nn.BatchNorm2d(out_channels),
            Swish()
        )
        # Xavier initialization
        init.xavier_uniform_(self.conv1[0].weight)

        self.conv2 = nn.Sequential(
            nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm2d(out_channels)
        )
        # Xavier initialization
        init.xavier_uniform_(self.conv2[0].weight)

        self.downsample = downsample
        if self.downsample:
            # Xavier initialization
            init.xavier_uniform_(self.downsample[0].weight)
        self.Swish = Swish()
        self.dropout = nn.Dropout(p=0.5)  # Dropout layer 추가
        self.out_channels = out_channels

    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.conv2(out)
        if self.downsample:
            residual = self.downsample(x)
        out += residual
        out = self.Swish(out)
        # out = self.dropout(out)  # Dropout 적용
        return out
