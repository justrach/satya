import json
import matplotlib.pyplot as plt
import seaborn as sns
import os

def create_github_comparison_plot(results, output_dir="benchmark_plots"):
    """Create GitHub API benchmark visualization"""
    plt.figure(figsize=(12, 6))
    
    # Extract data
    frameworks = []
    ops_per_sec = []
    batch_sizes = []
    
    for key, value in results["github"].items():
        if key == "pydantic":
            frameworks.append("Pydantic")
            ops_per_sec.append(value["ops_per_sec"])
            batch_sizes.append("N/A")
        else:
            frameworks.append("Satya")
            ops_per_sec.append(value["ops_per_sec"])
            batch_sizes.append(key.split("_")[1])
    
    # Create bar plot
    plt.figure(figsize=(10, 6))
    bars = plt.bar(range(len(frameworks)), ops_per_sec)
    
    # Customize plot
    plt.title("GitHub API Validation Performance", fontsize=14, pad=20)
    plt.xlabel("Framework & Batch Size")
    plt.ylabel("Operations per Second")
    plt.xticks(range(len(frameworks)), [f"{f}\n(batch={b})" for f, b in zip(frameworks, batch_sizes)])
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,.0f}',
                ha='center', va='bottom')
    
    # Color bars
    for i, bar in enumerate(bars):
        bar.set_color('blue' if 'Satya' in frameworks[i] else 'orange')
    
    plt.grid(True, axis='y', alpha=0.3)
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f"{output_dir}/github_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()

def create_posts_comparison_plot(results, output_dir="benchmark_plots"):
    """Create Posts API benchmark visualization"""
    for count_key, count_data in results["posts"].items():
        plt.figure(figsize=(12, 6))
        
        # Extract data
        labels = []
        ops_per_sec = []
        
        # Add Satya data
        for batch_key, batch_data in count_data["satya"].items():
            labels.append(f"Satya\n(batch={batch_key.split('_')[1]})")
            ops_per_sec.append(batch_data["ops_per_sec"])
        
        # Add Pydantic data
        labels.append("Pydantic")
        ops_per_sec.append(count_data["pydantic"]["ops_per_sec"])
        
        # Create bar plot
        bars = plt.bar(range(len(labels)), ops_per_sec)
        
        # Customize plot
        post_count = count_key.split("_")[1]
        plt.title(f"Posts API Validation Performance ({post_count} posts)", fontsize=14, pad=20)
        plt.xlabel("Framework & Batch Size")
        plt.ylabel("Operations per Second")
        plt.xticks(range(len(labels)), labels)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:,.0f}',
                    ha='center', va='bottom')
        
        # Color bars
        for i, bar in enumerate(bars):
            bar.set_color('blue' if 'Satya' in labels[i] else 'orange')
        
        plt.grid(True, axis='y', alpha=0.3)
        os.makedirs(output_dir, exist_ok=True)
        plt.savefig(f"{output_dir}/posts_comparison_{post_count}.png", dpi=300, bbox_inches='tight')
        plt.close()

def create_summary_plot(results, output_dir="benchmark_plots"):
    """Create overall performance summary plot"""
    plt.figure(figsize=(15, 10))
    plt.suptitle('Satya vs Pydantic Performance Summary', fontsize=16, y=0.95)
    
    # Create 2x2 subplot grid
    gs = plt.GridSpec(2, 2)
    
    # 1. GitHub API Performance (top left)
    ax1 = plt.subplot(gs[0, 0])
    github_data = results["github"]
    satya_ops = [v["ops_per_sec"] for k, v in github_data.items() if k.startswith("satya")]
    pydantic_ops = github_data["pydantic"]["ops_per_sec"]
    
    batch_sizes = [int(k.split("_")[1]) for k in github_data.keys() if k.startswith("satya")]
    ax1.plot(batch_sizes, satya_ops, 'bo-', label='Satya')
    ax1.axhline(y=pydantic_ops, color='orange', linestyle='--', label='Pydantic')
    
    ax1.set_title('GitHub API Performance')
    ax1.set_xlabel('Batch Size')
    ax1.set_ylabel('Operations per Second')
    ax1.legend()
    ax1.grid(True)
    
    # 2. Posts API Scaling (top right)
    ax2 = plt.subplot(gs[0, 1])
    post_counts = [int(k.split("_")[1]) for k in results["posts"].keys()]
    
    for batch_size in [1, 5, 10]:
        satya_ops = [results["posts"][f"count_{count}"]["satya"][f"batch_{batch_size}"]["ops_per_sec"] 
                     for count in post_counts]
        ax2.plot(post_counts, satya_ops, 'o-', label=f'Satya (batch={batch_size})')
    
    pydantic_ops = [results["posts"][f"count_{count}"]["pydantic"]["ops_per_sec"] 
                    for count in post_counts]
    ax2.plot(post_counts, pydantic_ops, 's--', label='Pydantic')
    
    ax2.set_title('Posts API Scaling')
    ax2.set_xlabel('Number of Posts')
    ax2.set_ylabel('Operations per Second')
    ax2.legend()
    ax2.grid(True)
    
    # 3. Speedup vs Batch Size (bottom left)
    ax3 = plt.subplot(gs[1, 0])
    speedups = [ops/github_data["pydantic"]["ops_per_sec"] for ops in satya_ops]
    ax3.plot(batch_sizes, speedups, 'bo-')
    ax3.set_title('Satya Speedup vs Batch Size (GitHub API)')
    ax3.set_xlabel('Batch Size')
    ax3.set_ylabel('Speedup (x times faster)')
    ax3.grid(True)
    
    # 4. Posts API Speedup (bottom right)
    ax4 = plt.subplot(gs[1, 1])
    for batch_size in [1, 5, 10]:
        speedups = []
        for count in post_counts:
            satya_perf = results["posts"][f"count_{count}"]["satya"][f"batch_{batch_size}"]["ops_per_sec"]
            pydantic_perf = results["posts"][f"count_{count}"]["pydantic"]["ops_per_sec"]
            speedups.append(satya_perf/pydantic_perf)
        ax4.plot(post_counts, speedups, 'o-', label=f'Batch={batch_size}')
    
    ax4.set_title('Satya Speedup vs Post Count')
    ax4.set_xlabel('Number of Posts')
    ax4.set_ylabel('Speedup (x times faster)')
    ax4.legend()
    ax4.grid(True)
    
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(f"{output_dir}/performance_summary.png", dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Load results
    with open("real_world_benchmark_results.json", "r") as f:
        results = json.load(f)
    
    # Create visualizations
    create_github_comparison_plot(results)
    create_posts_comparison_plot(results)
    create_summary_plot(results)

if __name__ == "__main__":
    main() 