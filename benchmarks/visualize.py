#!/usr/bin/env python3
"""
Visualization module for Satya benchmarks.
Creates flashy, professional charts to showcase Satya's performance.
"""

import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors
import matplotlib as mpl
from matplotlib.ticker import FuncFormatter
import json
import os
import argparse
from pathlib import Path

# Set global matplotlib parameters for consistent styling
plt.style.use('ggplot')
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif']

# Define color schemes
SATYA_COLOR = '#FF5757'  # Bright red for Satya
PYDANTIC_COLOR = '#4D4DFF'  # Blue for Pydantic
MSGSPEC_COLOR = '#4CAF50'  # Green for msgspec

def format_number(x, pos):
    """Format large numbers with commas"""
    if x >= 1e6:
        return f'{x*1e-6:.1f}M'
    elif x >= 1e3:
        return f'{x*1e-3:.1f}K'
    else:
        return f'{x:.1f}'

def create_horizontal_bar_chart(results, output_dir):
    """
    Create a flashy horizontal bar chart visualization of the benchmark results
    
    Args:
        results: Dictionary containing benchmark results
        output_dir: Directory to save the visualization
    """
    # Extract data from results
    categories = ['Validation\n(items/sec)', 'Memory\nEfficiency', 'Serialization\n(speed)', 'Deserialization\n(speed)', 'Strict Validation\n(speed)']
    
    # Calculate relative performance (higher is better)
    pydantic_rel = [
        results['validation']['pydantic_ips'] / results['validation']['satya_ips'],
        results['memory']['pydantic'] / results['memory']['satya'],
        results['serialization']['pydantic'][0] / results['serialization']['satya'][0],
        results['serialization']['pydantic'][1] / results['serialization']['satya'][1],
        results['strict']['pydantic'] / results['strict']['satya']
    ]
    
    msgspec_rel = [
        results['validation']['msgspec_ips'] / results['validation']['satya_ips'],
        results['memory']['msgspec'] / results['memory']['satya'],
        results['serialization']['msgspec'][0] / results['serialization']['satya'][0],
        results['serialization']['msgspec'][1] / results['serialization']['satya'][1],
        results['strict']['msgspec'] / results['strict']['satya']
    ]
    
    # Satya is always 1.0 (the baseline)
    satya_rel = [1.0, 1.0, 1.0, 1.0, 1.0]
    
    # Invert values where lower is better (all of them in this case)
    # For all metrics, we want higher bars to mean "better"
    pydantic_rel = [1/x for x in pydantic_rel]
    msgspec_rel = [1/x for x in msgspec_rel]
    
    # Create figure with a specific size
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Set up positions for bars
    y_pos = np.arange(len(categories))
    bar_width = 0.25
    
    # Create gradient effect for Satya bars
    satya_cmap = mcolors.LinearSegmentedColormap.from_list("", ["#FF8A8A", "#FF5757", "#B71C1C"])
    satya_colors = [satya_cmap(i/len(satya_rel)) for i in range(len(satya_rel))]
    
    # Plot horizontal bars with a slight shadow effect for depth
    ax.barh(y_pos - bar_width, satya_rel, bar_width, color=satya_colors, 
            label='Satya', edgecolor='white', linewidth=1, alpha=0.9, zorder=3)
    ax.barh(y_pos, pydantic_rel, bar_width, color=PYDANTIC_COLOR, 
            label='Pydantic', edgecolor='white', linewidth=1, alpha=0.7, zorder=2)
    ax.barh(y_pos + bar_width, msgspec_rel, bar_width, color=MSGSPEC_COLOR, 
            label='msgspec', edgecolor='white', linewidth=1, alpha=0.7, zorder=1)
    
    # Add value labels on the bars
    for i, v in enumerate(satya_rel):
        ax.text(v + 0.1, i - bar_width, f"{v:.1f}x", 
                va='center', fontweight='bold', color=SATYA_COLOR)
    
    for i, v in enumerate(pydantic_rel):
        ax.text(v + 0.1, i, f"{v:.1f}x", 
                va='center', fontweight='bold', color=PYDANTIC_COLOR)
    
    for i, v in enumerate(msgspec_rel):
        ax.text(v + 0.1, i + bar_width, f"{v:.1f}x", 
                va='center', fontweight='bold', color=MSGSPEC_COLOR)
    
    # Customize the plot
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=12, fontweight='bold')
    ax.set_xlabel('Relative Performance (higher is better)', fontsize=14, fontweight='bold')
    ax.set_title('Satya Performance Benchmark', fontsize=20, fontweight='bold', pad=20)
    
    # Add a subtitle explaining the chart
    plt.figtext(0.5, 0.01, 
                'Bar height represents relative performance.\nSatya (1.0x) is the baseline. Higher bars mean better performance.', 
                ha='center', fontsize=12, fontstyle='italic')
    
    # Add a grid for better readability (only horizontal lines)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add legend with custom styling
    legend = ax.legend(loc='upper right', fontsize=12, frameon=True, framealpha=0.9)
    frame = legend.get_frame()
    frame.set_facecolor('white')
    frame.set_edgecolor('#CCCCCC')
    
    # Add a watermark-style text
    fig.text(0.95, 0.05, 'Powered by Satya', 
             fontsize=12, color='gray', alpha=0.5,
             ha='right', va='bottom', rotation=0)
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    
    # Save the visualization
    output_path = os.path.join(output_dir, 'satya_performance_horizontal.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.replace('.png', '.pdf'), bbox_inches='tight')
    
    print(f"\nHorizontal bar chart saved to '{output_path}'")
    
    # Close the figure to free memory
    plt.close(fig)

def create_speed_comparison_chart(results, output_dir):
    """
    Create a chart specifically focused on validation speed
    
    Args:
        results: Dictionary containing benchmark results
        output_dir: Directory to save the visualization
    """
    # Extract validation speeds
    satya_speed = results['validation']['satya_ips']
    pydantic_speed = results['validation']['pydantic_ips']
    msgspec_speed = results['validation']['msgspec_ips']
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Set up bar positions
    bar_positions = np.arange(3)
    bar_width = 0.6
    
    # Create gradient for Satya bar
    satya_cmap = mcolors.LinearSegmentedColormap.from_list("", ["#FF8A8A", "#FF5757", "#B71C1C"])
    
    # Plot bars with 3D effect
    bars = ax.bar(bar_positions, [satya_speed, pydantic_speed, msgspec_speed], 
                  width=bar_width, 
                  color=[SATYA_COLOR, PYDANTIC_COLOR, MSGSPEC_COLOR],
                  edgecolor='white', linewidth=1)
    
    # Add value labels on top of bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.05*satya_speed,
                f'{height:,.0f}',
                ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Add relative performance labels
    ax.text(0, satya_speed * 0.5, "1.0x", ha='center', va='center', 
            fontsize=14, fontweight='bold', color='white')
    ax.text(1, pydantic_speed * 0.5, f"{satya_speed/pydantic_speed:.1f}x faster", 
            ha='center', va='center', fontsize=14, fontweight='bold', color='white')
    ax.text(2, msgspec_speed * 0.5, f"{satya_speed/msgspec_speed:.1f}x faster", 
            ha='center', va='center', fontsize=14, fontweight='bold', color='white')
    
    # Customize the plot
    ax.set_xticks(bar_positions)
    ax.set_xticklabels(['Satya', 'Pydantic', 'msgspec'], fontsize=14, fontweight='bold')
    ax.set_ylabel('Validations per Second', fontsize=14, fontweight='bold')
    ax.set_title('Validation Speed Comparison', fontsize=20, fontweight='bold', pad=20)
    
    # Format y-axis with K/M suffixes
    ax.yaxis.set_major_formatter(FuncFormatter(format_number))
    
    # Add a grid for better readability
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Add a subtitle
    plt.figtext(0.5, 0.01, 
                f'Satya validates {satya_speed:,.0f} items per second, making it\n{satya_speed/pydantic_speed:.1f}x faster than Pydantic and {satya_speed/msgspec_speed:.1f}x faster than msgspec', 
                ha='center', fontsize=12, fontstyle='italic')
    
    # Adjust layout and save
    plt.tight_layout(rect=[0, 0.05, 1, 0.97])
    
    # Save the visualization
    output_path = os.path.join(output_dir, 'satya_speed_comparison.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.replace('.png', '.pdf'), bbox_inches='tight')
    
    print(f"Speed comparison chart saved to '{output_path}'")
    
    # Close the figure to free memory
    plt.close(fig)

def create_dashboard(results, output_dir):
    """
    Create a comprehensive dashboard with multiple visualizations
    
    Args:
        results: Dictionary containing benchmark results
        output_dir: Directory to save the visualization
    """
    # Create a figure with subplots
    fig = plt.figure(figsize=(16, 12))
    
    # Define grid layout
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 0.8])
    
    # Extract data
    validation_speeds = [
        results['validation']['satya_ips'],
        results['validation']['pydantic_ips'],
        results['validation']['msgspec_ips']
    ]
    
    memory_usage = [
        results['memory']['satya'],
        results['memory']['pydantic'],
        results['memory']['msgspec']
    ]
    
    serialization_times = [
        results['serialization']['satya'][0],
        results['serialization']['pydantic'][0],
        results['serialization']['msgspec'][0]
    ]
    
    deserialization_times = [
        results['serialization']['satya'][1],
        results['serialization']['pydantic'][1],
        results['serialization']['msgspec'][1]
    ]
    
    strict_times = [
        results['strict']['satya'],
        results['strict']['pydantic'],
        results['strict']['msgspec']
    ]
    
    # 1. Validation Speed Chart (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    bars1 = ax1.bar(
        np.arange(3), 
        validation_speeds,
        color=[SATYA_COLOR, PYDANTIC_COLOR, MSGSPEC_COLOR],
        edgecolor='white', linewidth=1
    )
    
    # Add value labels
    for i, bar in enumerate(bars1):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height * 1.02,
                f'{height:,.0f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax1.set_xticks(np.arange(3))
    ax1.set_xticklabels(['Satya', 'Pydantic', 'msgspec'], fontsize=10, fontweight='bold')
    ax1.set_title('Validation Speed (items/sec)', fontsize=14, fontweight='bold')
    ax1.yaxis.set_major_formatter(FuncFormatter(format_number))
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    ax1.set_axisbelow(True)
    
    # 2. Memory Usage Chart (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    bars2 = ax2.bar(
        np.arange(3), 
        memory_usage,
        color=[SATYA_COLOR, PYDANTIC_COLOR, MSGSPEC_COLOR],
        edgecolor='white', linewidth=1
    )
    
    # Add value labels
    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height * 1.02,
                f'{height:.1f} MB',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax2.set_xticks(np.arange(3))
    ax2.set_xticklabels(['Satya', 'Pydantic', 'msgspec'], fontsize=10, fontweight='bold')
    ax2.set_title('Memory Usage (MB)', fontsize=14, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    ax2.set_axisbelow(True)
    
    # 3. Serialization Time Chart (middle left)
    ax3 = fig.add_subplot(gs[1, 0])
    bars3 = ax3.bar(
        np.arange(3), 
        serialization_times,
        color=[SATYA_COLOR, PYDANTIC_COLOR, MSGSPEC_COLOR],
        edgecolor='white', linewidth=1
    )
    
    # Add value labels
    for i, bar in enumerate(bars3):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height * 1.02,
                f'{height:.4f} s',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax3.set_xticks(np.arange(3))
    ax3.set_xticklabels(['Satya', 'Pydantic', 'msgspec'], fontsize=10, fontweight='bold')
    ax3.set_title('Serialization Time (lower is better)', fontsize=14, fontweight='bold')
    ax3.grid(axis='y', linestyle='--', alpha=0.7)
    ax3.set_axisbelow(True)
    
    # 4. Deserialization Time Chart (middle right)
    ax4 = fig.add_subplot(gs[1, 1])
    bars4 = ax4.bar(
        np.arange(3), 
        deserialization_times,
        color=[SATYA_COLOR, PYDANTIC_COLOR, MSGSPEC_COLOR],
        edgecolor='white', linewidth=1
    )
    
    # Add value labels
    for i, bar in enumerate(bars4):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height * 1.02,
                f'{height:.4f} s',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax4.set_xticks(np.arange(3))
    ax4.set_xticklabels(['Satya', 'Pydantic', 'msgspec'], fontsize=10, fontweight='bold')
    ax4.set_title('Deserialization Time (lower is better)', fontsize=14, fontweight='bold')
    ax4.grid(axis='y', linestyle='--', alpha=0.7)
    ax4.set_axisbelow(True)
    
    # 5. Performance Summary (bottom spanning both columns)
    ax5 = fig.add_subplot(gs[2, :])
    
    # Calculate relative performance metrics
    rel_validation = [
        1.0,
        validation_speeds[0] / validation_speeds[1],
        validation_speeds[0] / validation_speeds[2]
    ]
    
    rel_memory = [
        1.0,
        memory_usage[1] / memory_usage[0],
        memory_usage[2] / memory_usage[0]
    ]
    
    rel_serialization = [
        1.0,
        serialization_times[1] / serialization_times[0],
        serialization_times[2] / serialization_times[0]
    ]
    
    rel_deserialization = [
        1.0,
        deserialization_times[1] / deserialization_times[0],
        deserialization_times[2] / deserialization_times[0]
    ]
    
    rel_strict = [
        1.0,
        strict_times[1] / strict_times[0],
        strict_times[2] / strict_times[0]
    ]
    
    # Create a table for the summary
    cell_text = [
        [f"{rel_validation[0]:.1f}x", f"{rel_validation[1]:.1f}x", f"{rel_validation[2]:.1f}x"],
        [f"{rel_memory[0]:.1f}x", f"{rel_memory[1]:.1f}x", f"{rel_memory[2]:.1f}x"],
        [f"{rel_serialization[0]:.1f}x", f"{rel_serialization[1]:.1f}x", f"{rel_serialization[2]:.1f}x"],
        [f"{rel_deserialization[0]:.1f}x", f"{rel_deserialization[1]:.1f}x", f"{rel_deserialization[2]:.1f}x"],
        [f"{rel_strict[0]:.1f}x", f"{rel_strict[1]:.1f}x", f"{rel_strict[2]:.1f}x"]
    ]
    
    row_labels = ['Validation Speed', 'Memory Efficiency', 'Serialization', 'Deserialization', 'Strict Validation']
    col_labels = ['Satya (baseline)', 'vs Pydantic', 'vs msgspec']
    
    # Hide axes
    ax5.axis('off')
    
    # Create table
    table = ax5.table(
        cellText=cell_text,
        rowLabels=row_labels,
        colLabels=col_labels,
        loc='center',
        cellLoc='center'
    )
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 1.5)
    
    # Color the cells based on performance (green for good, yellow for neutral, red for bad)
    for i in range(len(row_labels)):
        for j in range(len(col_labels)):
            cell = table[(i+1, j)]
            if j == 0:  # Baseline column
                cell.set_facecolor('#f0f0f0')
            else:
                # Extract the numeric value
                value = float(cell_text[i][j].replace('x', ''))
                if value > 1.0:  # Better than baseline
                    # Shade of green based on how much better
                    intensity = min(1.0, (value - 1.0) / 5.0 + 0.2)
                    cell.set_facecolor((0.2, 0.8 * intensity + 0.2, 0.2))
                    cell.set_text_props(color='white', fontweight='bold')
                else:  # Worse than baseline
                    # Shade of red based on how much worse
                    intensity = min(1.0, (1.0 - value) / 0.5 + 0.2)
                    cell.set_facecolor((0.8 * intensity + 0.2, 0.2, 0.2))
                    cell.set_text_props(color='white', fontweight='bold')
    
    # Add title for the table
    ax5.set_title('Relative Performance (higher is better)', fontsize=14, fontweight='bold')
    
    # Add overall title for the dashboard
    fig.suptitle('Satya Performance Dashboard', fontsize=20, fontweight='bold', y=0.98)
    
    # Add a watermark-style text
    fig.text(0.95, 0.01, 'Powered by Satya', 
             fontsize=10, color='gray', alpha=0.5,
             ha='right', va='bottom', rotation=0)
    
    # Adjust layout and save
    plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.95])
    
    # Save the visualization
    output_path = os.path.join(output_dir, 'satya_dashboard.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.savefig(output_path.replace('.png', '.pdf'), bbox_inches='tight')
    
    print(f"Dashboard saved to '{output_path}'")
    
    # Close the figure to free memory
    plt.close(fig)

def load_results_from_file(file_path):
    """Load benchmark results from a JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_results_to_file(results, output_dir):
    """Save benchmark results to a JSON file"""
    output_path = os.path.join(output_dir, 'benchmark_results.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to '{output_path}'")

def main():
    """Main function to generate visualizations from benchmark results"""
    parser = argparse.ArgumentParser(description='Generate visualizations for Satya benchmarks')
    parser.add_argument('--results', type=str, help='Path to JSON file with benchmark results')
    parser.add_argument('--output-dir', type=str, default='benchmarks/results', 
                        help='Directory to save visualizations')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load results from file if provided
    if args.results:
        results = load_results_from_file(args.results)
    else:
        # Example results for testing
        results = {
            'validation': {
                'pydantic_ips': 100000,
                'satya_ips': 500000,
                'msgspec_ips': 300000
            },
            'memory': {
                'pydantic': 150,
                'satya': 50,
                'msgspec': 80
            },
            'serialization': {
                'pydantic': (0.5, 0.8),
                'satya': (0.3, 0.4),
                'msgspec': (0.1, 0.2)
            },
            'strict': {
                'pydantic': 0.6,
                'satya': 0.2,
                'msgspec': 0.3
            }
        }
    
    # Generate visualizations
    create_horizontal_bar_chart(results, args.output_dir)
    create_speed_comparison_chart(results, args.output_dir)
    create_dashboard(results, args.output_dir)
    
    print("\nAll visualizations generated successfully!")

if __name__ == "__main__":
    main() 