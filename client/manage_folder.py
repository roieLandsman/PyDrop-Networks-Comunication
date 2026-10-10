from pathlib import Path
from client.constants import STATE_FILE_NAME
from client.file_utils import file_metadata
from log import log
from client.validation import validate_filename


class Folder():
    def __init__(self, path: Path) -> None:
        "initizlize the tracking of the scanned folder"
        self.path = path
        self.files = dict()
        self.local_files = set()
        self.sub_dirs = set()
        
        self.path.mkdir(parents=True, exist_ok=True)
        
        self.refresh()
    
    def refresh(self) -> None:
      "resresh the state of the fodler sccording to real changes in the local files"
      self.files = dict()
      self.local_files = set()
      self.sub_dirs = set()
      
      for sub_path in self.path.iterdir():
          if not sub_path.is_file():
              self.sub_dirs.add(sub_path)
          elif sub_path.name == STATE_FILE_NAME:
              continue
          elif sub_path.name.endswith(".local"):
              self.local_files.add(sub_path)
          else:
              try:
                  validate_filename(sub_path.name)
              except ValueError as error:
                  log.error(f"skipped invalid local filename {sub_path.name}: {error}")
                  continue
              self.files[sub_path.name] = file_metadata(sub_path)
    
    def get_diff(self, old_snapshot: dict) -> dict:
      "compare the current fodler state to the old snapshot"
      def modified(old):
        modified_files = list()
        common_names = set(old_data) & set(self.files)

        for name in common_names:
            old_hash = old_data[name].get("hash")
            current_hash = self.files[name].get("hash")

            if old_hash != current_hash:
                modified_files.append(name)

        return sorted(modified_files)
      
      old_data = old_snapshot.files if isinstance(old_snapshot, Folder) else old_snapshot
      file_names = set(self.files.keys())
      old_file_names = set(old_data.keys())
      
      return {"added": sorted(file_names - old_file_names),
              "modified": modified(old_data),
              "deleted": sorted(old_file_names - file_names)
            }
  
    def get_single_file_metadata(self, filename: str) -> dict:
      "get the metadata of a single file"
      return self.files.get(filename)
    
    def update_single_file_metadata(self, filename: str, metadata: dict) -> None:
      "update the metadata of a single file"
      self.files[filename] = metadata
    
    def delete_file(self, filename: str) -> None:
      "remove a file from the fodler state"
      if filename in self.files.keys():
        self.files.pop(filename) 

    def export(self) -> dict:
        "return a copy of the fodler state data"
        return self.files.copy()
        