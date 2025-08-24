"""
Jupyter notebooks for F1 GP Predictor analysis and exploration.

Contains notebooks for:
- Circuit analysis and visualization
- Driver performance analysis  
- Prediction model validation
- Data exploration and insights
"""

# Notebook utilities
import warnings
warnings.filterwarnings('ignore')

def setup_notebook_environment():
    """Setup environment for Jupyter notebooks."""
    import sys
    from pathlib import Path
    
    # Add project root to path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Configure plotting
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Configure for better display
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 12
        
        print("✅ Notebook environment configured")
        print("📊 Matplotlib and Seaborn ready for plotting")
        
    except ImportError:
        print("⚠️  Plotting libraries not available")
    
    return True

# Auto-setup when imported
try:
    setup_notebook_environment()
except Exception as e:
    print(f"⚠️  Notebook setup warning: {e}")

__all__ = [
    "setup_notebook_environment"
]
