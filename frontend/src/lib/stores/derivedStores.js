import { derived } from 'svelte/store';
import { currentProject } from './projectStore';
import { videoState } from './videoPlayerStore';

// Derived stores
export const activeCaption = derived(
  [currentProject, videoState],
  ([$project, $video]) => {
    if (!$project) return null;
    return $project.captions.find(c => 
      $video.currentTime >= c.start && $video.currentTime <= c.end
    ) || null;
  }
);

export const activeWord = derived(
  [activeCaption, videoState],
  ([$caption, $video]) => {
    if (!$caption || !$caption.words) return null;
    return $caption.words.find(w => 
      $video.currentTime >= w.start && $video.currentTime <= w.end
    ) || null;
  }
);