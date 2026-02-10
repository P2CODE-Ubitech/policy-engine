import shutil
import subprocess
import os

def helm_package_and_push(
    application_name: str,
    version: str,
    chart_path: str = ".",
    registry_url: str = None
) -> bool:
    target_registry = registry_url or Config.HELM_REGISTRY
    
    try:
        ## Package the chart
        package_cmd = ["helm", "package", str(chart_path)]
        subprocess.run(package_cmd, check=True)
        
        ## Identify the file (Helm names it: name-version.tgz)
        package_file = f"{application_name}-{version}.tgz"
        
        ## Push to registry
        push_cmd = ["helm", "push", package_file, target_registry]
        subprocess.run(push_cmd, check=True)
        
        ## Cleanup
        if os.path.exists(package_file):
            os.remove(package_file)
            
        return True

    except subprocess.CalledProcessError as e:
        print(f"!!! Helm Command Failed: {e.cmd}")
        print(f"!!! Output: {e.output}")
        return False # This tells the caller that it failed!
