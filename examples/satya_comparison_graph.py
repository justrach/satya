#!/usr/bin/env python3
"""
Create a focused comparison graph for Satya's JSON methods
"""

import matplotlib.pyplot as plt
import numpy as np

def create_satya_comparison():
    """Create a focused comparison of Satya's JSON methods"""
    
    # Data from the benchmark results
    methods = [
        'json.dumps\n(baseline)',
        'orjson.dumps',
        'msgspec.encode',
        'Satya\nModel.json()',
        'orjson +\nSatya.dict()',
        'Satya\nvalidator.to_json()'
    ]
    
    # Serialization performance (ops/sec)
    serialization_ops = [580456, 4081244, 3727403, 3050082, 3354119, 56737]
    
    # Parsing performance (ops/sec) 
    parsing_methods = [
        'json.loads\n(baseline)',
        'orjson.loads',
        'msgspec.decode',
        'Satya\nModel.from_json()',
        'Satya\nvalidator.from_json()'
    ]
    parsing_ops = [699965, 1856404, 1921596, 776994, 63128]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Satya JSON Performance Comparison', fontsize=16, fontweight='bold')
    
    # Colors for different categories
    colors_ser = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    colors_par = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#DDA0DD']
    
    # Serialization chart
    bars1 = ax1.bar(range(len(methods)), serialization_ops, color=colors_ser)
    ax1.set_title('JSON Serialization Performance\n(Higher is Better)', fontweight='bold', pad=20)
    ax1.set_ylabel('Operations per Second')
    ax1.set_xticks(range(len(methods)))
    ax1.set_xticklabels(methods, rotation=0, ha='center')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
    
    # Add value labels on bars
    for bar, ops_val in zip(bars1, serialization_ops):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                f'{ops_val/1000:.0f}K', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Parsing chart
    bars2 = ax2.bar(range(len(parsing_methods)), parsing_ops, color=colors_par)
    ax2.set_title('JSON Parsing Performance\n(Higher is Better)', fontweight='bold', pad=20)
    ax2.set_ylabel('Operations per Second')
    ax2.set_xticks(range(len(parsing_methods)))
    ax2.set_xticklabels(parsing_methods, rotation=0, ha='center')
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}K'))
    
    # Add value labels on bars
    for bar, ops_val in zip(bars2, parsing_ops):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                f'{ops_val/1000:.0f}K', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Add performance insights as text
    insights_text = """
Key Performance Insights:

🚀 Serialization:
• orjson.dumps(): 7.0x faster than json.dumps
• msgspec.encode(): 6.4x faster than json.dumps  
• Satya Model.json(): 5.3x faster than json.dumps
• orjson + Satya.dict(): 5.8x faster than json.dumps

🔄 Parsing:
• orjson.loads(): 2.7x faster than json.loads
• msgspec.decode(): 2.8x faster than json.loads
• Satya Model.from_json(): 1.1x faster than json.loads

💡 Satya provides validation + performance in one package!
"""
    
    plt.figtext(0.02, 0.02, insights_text, fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8))
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.35)  # Make room for insights text
    plt.savefig('satya_performance_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    print("📊 Satya comparison graph saved as 'satya_performance_comparison.png'")

if __name__ == "__main__":
    create_satya_comparison() 