## Visualizations

The benchmarks include visualization capabilities to help showcase Satya's performance:

### Automatic Visualization

When you run `benchmark_msgspec.py`, it automatically generates several visualizations:

1. **Horizontal Bar Chart**: Shows relative performance of Satya compared to Pydantic and msgspec
2. **Speed Comparison Chart**: Focuses specifically on validation speed
3. **Performance Dashboard**: A comprehensive view of all performance metrics

All visualizations are saved to the `benchmarks/results` directory in both PNG and PDF formats.

### Manual Visualization

You can also generate visualizations separately using the `visualize.py` script:

```bash
python benchmarks/visualize.py --results benchmarks/results/benchmark_results.json
```

### Visualization Requirements

To generate visualizations, you need to install matplotlib:

```bash
pip install matplotlib
```

## Example Visualization

![Satya Performance Dashboard](https://raw.githubusercontent.com/your-username/satya/main/benchmarks/results/satya_dashboard.png)

## Requirements

To run the benchmarks, you need to install the following packages:

```bash
pip install satya pydantic msgspec psutil matplotlib
``` 