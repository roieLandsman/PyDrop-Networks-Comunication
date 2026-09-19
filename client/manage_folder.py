from pathlib import Path

from client.constants import STATE_FILE_NAME
from client.file_utils import file_metadata
from log import log
from client.validation import validate_filename


class Folder():
    def __init__(self, path: Path) -> None:
        """Create a folder scanner for one local sync folder."""
        self.path = path
        self.files = dict()
        self.local_files = set()
        self.sub_dirs = set()
        
        self.path.mkdir(parents=True, exist_ok=True)
        
        self.refresh()
    
    def refresh(self) -> None:
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
      """Return added, modified, and deleted filenames."""
      old_data = old_snapshot.files if isinstance(old_snapshot, Folder) else old_snapshot
      file_names = set(self.files.keys())
      old_file_names = set(old_data.keys())
      
      return {"added": sorted(file_names - old_file_names),
              "modified": sorted(name for name in old_file_names & file_names
                                 if old_data[name].get("hash") != self.files[name].get("hash")),
              "deleted": sorted(old_file_names - file_names)
            }
  
    def get_single_file_metadata(self, filename: str) -> dict:
      """Return tracked metadata for one file name."""
      return self.files.get(filename)
    
    def update_single_file_metadata(self, filename: str, metadata: dict) -> None:
      """Store tracked metadata for one file name."""
      self.files[filename] = metadata
    
    def delete_file(self, filename: str) -> None:
      """Remove one file name from tracked metadata."""
      if filename in self.files.keys():
        self.files.pop(filename) 

    def export(self) -> dict:
        """Return a copy of the current file metadata."""
        return self.files.copy()
        