对指定A股股票进行全面评估，输出结构化报告。

## 输入参数

$ARGUMENTS

## 执行流程

请先读取 skill 模板文件，然后按模板中的步骤执行评估：

```bash
python3 -c "from hermes.resources import get_skill; print(get_skill('evaluate_stock'))"
```

将输出内容作为完整评估流程执行。