from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

# Type aliases for better readability
NoteDict = Dict[str, Any]
NoteList = List[NoteDict]

@dataclass
class Note:
    """Represents a single note with metadata."""
    id: int
    text: str
    done: bool = False
    tags: List[str] = None
    created_at: str = None
    updated_at: str = None

    def to_dict(self) -> NoteDict:
        """Convert note to dictionary with default values for optional fields."""
        note_dict = asdict(self)
        current_time = datetime.now().isoformat(timespec="seconds")
        
        # Set defaults for optional fields
        note_dict["tags"] = note_dict.get("tags") or []
        note_dict["created_at"] = note_dict.get("created_at") or current_time
        note_dict["updated_at"] = note_dict.get("updated_at") or note_dict["created_at"]
        
        return note_dict 

class NoteStore:
    """Manages persistence of notes to a JSON file."""

    def __init__(self, path: Path = Path("notes.json")):
        """Initialize store with path to JSON file."""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> NoteList:
        """Read notes from JSON file. Returns empty list if file doesn't exist."""
        if not self.path.exists():
            return []
            
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write_atomic(self, notes: NoteList) -> None:
        """Write notes to file atomically using a temporary file."""
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
            
        os.replace(temp_path, self.path)  # atomic on POSIX/Windows

    def list(self, include_done: bool = True) -> NoteList:
        """List all notes, optionally filtering out completed ones."""
        notes = self._read()
        
        if not include_done:
            notes = [note for note in notes if not note.get("done")]
            
        return sorted(notes, key=lambda n: n.get("id", 0), reverse=True)

    def _next_id(self, notes: NoteList) -> int:
        """Generate next available note ID."""
        return max((note.get("id", 0) for note in notes), default=0) + 1

    def add(self, text: str, tags: Optional[List[str]] = None) -> NoteDict:
        """Add a new note with given text and optional tags."""
        notes = self._read()
        new_note = Note(id=self._next_id(notes), text=text, tags=tags or [])
        note_dict = new_note.to_dict()
        
        notes.append(note_dict)
        self._write_atomic(notes)
        
        return note_dict

    def _find_idx(self, notes: NoteList, note_id: int) -> int:
        """Find index of note by ID. Raises KeyError if not found."""
        for idx, note in enumerate(notes):
            if note.get("id") == note_id:
                return idx
        raise KeyError(f"Note {note_id} not found")

    def set_done(self, note_id: int, done: bool = True) -> NoteDict:
        """Mark note as done/undone."""
        notes = self._read()
        idx = self._find_idx(notes, note_id)
        
        notes[idx]["done"] = done
        notes[idx]["updated_at"] = datetime.now().isoformat(timespec="seconds")
        
        self._write_atomic(notes)
        return notes[idx]

    def edit(self, note_id: int, new_text: str) -> NoteDict:
        """Update note text."""
        notes = self._read()
        idx = self._find_idx(notes, note_id)
        
        notes[idx]["text"] = new_text
        notes[idx]["updated_at"] = datetime.now().isoformat(timespec="seconds")
        
        self._write_atomic(notes)
        return notes[idx]

    def remove(self, note_id: int) -> None:
        """Delete note by ID."""
        notes = self._read()
        idx = self._find_idx(notes, note_id)
        notes.pop(idx)
        self._write_atomic(notes)

    def search(self, query: str) -> NoteList:
        """Search notes by text content and tags."""
        query_lower = query.lower()
        
        def matches_query(note: NoteDict) -> bool:
            text_matches = query_lower in note.get("text", "").lower()
            tag_matches = any(query_lower in tag.lower() for tag in note.get("tags", []))
            return text_matches or tag_matches
            
        return [note for note in self._read() if matches_query(note)]
    
# Test the notes app properly
note_store = NoteStore()

# Add a single note
note = note_store.add("aiden's height", tags=["4ft11in", "short"])

# Mark it as done
note_store.set_done(note["id"], True)

# Verify the note was updated
print(note_store.list())