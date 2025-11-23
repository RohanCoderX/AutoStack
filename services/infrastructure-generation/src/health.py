import sys
import subprocess

def health_check():
    """Health check for Docker container"""
    try:
        # Check if Terraform is available
        result = subprocess.run(["terraform", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Health check failed: Terraform not available")
            sys.exit(1)
        
        print("Health check passed")
        sys.exit(0)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    health_check()