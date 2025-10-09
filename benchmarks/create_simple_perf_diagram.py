#!/usr/bin/env python3
"""
Create a simple horizontal performance comparison diagram.
Shows 3 key metrics: Single Validation, Batch Validation, Field Access
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Performance data (queries/sec)
metrics = ['Single Validation', 'Batch Validation', 'Field Access']
pydantic_perf = [1_020_000, 915_000, 65_300_000]  # queries/sec
satya_perf = [1_100_000, 5_000_000, 66_200_000]  # queries/sec

# Calculate speedups
speedups = [s/p for s, p in zip(satya_perf, pydantic_perf)]

# Create figure
fig, ax = plt.subplots(figsize=(14, 6))
fig.patch.set_facecolor('white')
ax.set_facecolor('#f8f9fa')

# Bar positions
y_pos = np.arange(len(metrics))
bar_height = 0.35

# Create bars - Pydantic pink/red, Satya blue/cyan (matching logo)
bars_pydantic = ax.barh(y_pos - bar_height/2, pydantic_perf, bar_height, 
                        label='Pydantic 2.12.0', color='#E92063', alpha=0.85, edgecolor='black', linewidth=1.5)
bars_satya = ax.barh(y_pos + bar_height/2, satya_perf, bar_height,
                     label='Satya 0.4.0', color='#00A8E8', alpha=0.85, edgecolor='black', linewidth=1.5)

# Customize
ax.set_yticks(y_pos)
ax.set_yticklabels(metrics, fontsize=13, fontweight='bold')
ax.set_xlabel('Performance (queries/second)', fontsize=14, fontweight='bold')
ax.set_title('Satya vs Pydantic 2.12.0 - Performance Comparison', 
             fontsize=16, fontweight='bold', pad=20)

# Format x-axis to show millions
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1_000_000:.1f}M' if x >= 1_000_000 else f'{x/1_000:.0f}K'))

# Add value labels on bars
for i, (bar_p, bar_s) in enumerate(zip(bars_pydantic, bars_satya)):
    # Pydantic label
    width_p = bar_p.get_width()
    label_p = f'{width_p/1_000_000:.2f}M/s' if width_p >= 1_000_000 else f'{width_p/1_000:.0f}K/s'
    ax.text(width_p, bar_p.get_y() + bar_p.get_height()/2, 
            f'  {label_p}', ha='left', va='center', fontsize=11, fontweight='bold')
    
    # Satya label with speedup
    width_s = bar_s.get_width()
    label_s = f'{width_s/1_000_000:.2f}M/s' if width_s >= 1_000_000 else f'{width_s/1_000:.0f}K/s'
    speedup_text = f'{speedups[i]:.2f}×' if speedups[i] < 2 else f'{speedups[i]:.1f}×'
    ax.text(width_s, bar_s.get_y() + bar_s.get_height()/2,
            f'  {label_s} ({speedup_text})', ha='left', va='center', 
            fontsize=11, fontweight='bold', color='#0066CC')

# Grid
ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.8)
ax.set_axisbelow(True)

# Legend
ax.legend(loc='lower right', fontsize=12, framealpha=0.95, edgecolor='black', fancybox=True)

# Tight layout
plt.tight_layout()

# Save
output_file = 'benchmarks/performance_comparison_simple.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ Saved performance diagram to: {output_file}")

# Also create a dark version
fig.patch.set_facecolor('#1a1a1a')
ax.set_facecolor('#2d2d2d')
ax.spines['bottom'].set_color('white')
ax.spines['top'].set_color('white')
ax.spines['left'].set_color('white')
ax.spines['right'].set_color('white')
ax.tick_params(colors='white')
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.title.set_color('white')
for label in ax.get_yticklabels():
    label.set_color('white')
for label in ax.get_xticklabels():
    label.set_color('white')

output_dark = 'benchmarks/performance_comparison_simple_dark.png'
plt.savefig(output_dark, dpi=300, bbox_inches='tight', facecolor='#1a1a1a')
print(f"✅ Saved dark version to: {output_dark}")

plt.close()
