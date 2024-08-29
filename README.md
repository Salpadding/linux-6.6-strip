# README

## 简介

暂时只计划支持在 x86_64 的 linux 系统上编译 ARCH=x86_64 的内核

## 修改记录
- 2024-08-29
  
主要改动是使用INDENT 环境变量追踪 make 的递归深度和当前的 target
目前可以 make defconfig, make nconfig, make mrproper 三步走了 下一步是尝试构建一些设备驱动以及添加 kbuild 相关的介绍

