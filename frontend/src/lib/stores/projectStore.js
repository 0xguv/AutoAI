import { writable } from 'svelte/store';

// Style Presets
export const STYLE_PRESETS = {
  'alex-hormozi': {
    fontFamily: 'Inter',
    fontWeight: '900',
    fontSize: 48,
    color: '#FFFFFF',
    backgroundColor: 'transparent',
    textTransform: 'uppercase',
    textShadow: 'heavy',
    animation: 'pop',
    position: 'bottom',
    alignment: 'center',
    highlightWords: true,
    highlightColor: '#FFD700',
    wordByWord: true,
    letterSpacing: 2,
    lineHeight: 1.2
  },
  'minimal': {
    fontFamily: 'Inter',
    fontWeight: 'normal',
    fontSize: 36,
    color: '#FFFFFF',
    backgroundColor: 'rgba(0,0,0,0.6)',
    textTransform: 'none',
    textShadow: 'light',
    animation: 'fade',
    position: 'bottom',
    alignment: 'center',
    highlightWords: false,
    wordByWord: false
  },
  'modern-vibe': {
    fontFamily: 'Inter',
    fontWeight: 'bold',
    fontSize: 42,
    color: '#FFFFFF',
    backgroundColor: 'transparent',
    textTransform: 'none',
    textShadow: 'medium',
    animation: 'slide-up',
    position: 'middle',
    alignment: 'center',
    highlightWords: true,
    highlightColor: '#FF6B6B',
    wordByWord: true
  },
  'tiktok-viral': {
    fontFamily: 'Inter',
    fontWeight: '900',
    fontSize: 52,
    color: '#FFFFFF',
    backgroundColor: 'transparent',
    textTransform: 'uppercase',
    textShadow: 'heavy',
    animation: 'bounce',
    position: 'middle',
    alignment: 'center',
    highlightWords: true,
    highlightColor: '#00F5FF',
    wordByWord: true,
    letterSpacing: 3
  }
};

// Default style
export const DEFAULT_STYLE = {
  fontFamily: 'Inter',
  fontSize: 42,
  fontWeight: 'bold',
  color: '#FFFFFF',
  backgroundColor: 'transparent',
  textTransform: 'none',
  textShadow: 'medium',
  animation: 'pop',
  position: 'bottom',
  alignment: 'center',
  letterSpacing: 0,
  lineHeight: 1.2,
  highlightWords: false,
  wordByWord: false
};

// Current project store
function createProjectStore() {
  const { subscribe, set, update } = writable({
    id: null,
    name: '',
    videoUrl: '',
    videoDuration: 0,
    captions: [],
    bRollClips: [],
    zoomEffects: [], // New: to store auto-generated zoom effects
    soundEffects: [], // New: to store auto-generated sound effects
    style: DEFAULT_STYLE, // Use DEFAULT_STYLE for new projects
    resolution: '1080x1920',
    createdAt: new Date(),
    updatedAt: new Date()
  });

  return {
    subscribe,
    set,
    update,
    updateCaption: (captionId, updates) => {
      update(project => {
        if (!project) return project;
        const captions = project.captions.map(c => 
          c.id === captionId ? { ...c, ...updates } : c
        );
        return { ...project, captions, updatedAt: new Date() };
      });
    },
    updateStyle: (style) => {
      update(project => {
        if (!project) return project;
        return { 
          ...project, 
          style: { ...project.style, ...style },
          updatedAt: new Date()
        };
      });
    },
    applyPreset: (presetName) => {
      update(project => {
        if (!project) return project;
        const preset = STYLE_PRESETS[presetName];
        if (!preset) return project;
        return {
          ...project,
          style: { ...DEFAULT_STYLE, ...preset },
          updatedAt: new Date()
        };
      });
    },
    addBRoll: (clip) => {
      update(project => {
        if (!project) return project;
        return {
          ...project,
          bRollClips: [...project.bRollClips, clip],
          updatedAt: new Date()
        };
      });
    },
    removeBRoll: (clipId) => {
      update(project => {
        if (!project) return project;
        return {
          ...project,
          bRollClips: project.bRollClips.filter(c => c.id !== clipId),
          updatedAt: new Date()
        };
      });
    },
    updateWordEmoji: (segmentId, wordIndex, emoji) => {
      update(project => {
        if (!project) return project;
        const updatedCaptions = project.captions.map(segment => {
          if (segment.id === segmentId) {
            const updatedWords = segment.words.map((word, index) => {
              if (index === wordIndex) {
                return { ...word, emoji: emoji || null }; // Set emoji or null if empty
              }
              return word;
            });
            return { ...segment, words: updatedWords };
          }
          return segment;
        });
        return { ...project, captions: updatedCaptions, updatedAt: new Date() };
      });
    },
    updateWordIsKeyword: (segmentId, wordIndex, isKeyword) => {
      update(project => {
        if (!project) return project;
        const updatedCaptions = project.captions.map(segment => {
          if (segment.id === segmentId) {
            const updatedWords = segment.words.map((word, index) => {
              if (index === wordIndex) {
                return { ...word, isKeyword: isKeyword };
              }
              return word;
            });
            return { ...segment, words: updatedWords };
          }
          return segment;
        });
        return { ...project, captions: updatedCaptions, updatedAt: new Date() };
      });
    },
    updateBRollClipStart: (clipId, newStart) => {
      update(project => {
        if (!project) return project;
        const updatedBRollClips = project.bRollClips.map(clip => {
          if (clip.id === clipId) {
            // Ensure newStart is not negative
            const safeNewStart = Math.max(0, newStart);
            return { ...clip, start: safeNewStart };
          }
          return clip;
        });
        return { ...project, bRollClips: updatedBRollClips, updatedAt: new Date() };
      });
    },
    updateBRollClipDuration: (clipId, newDuration) => {
      update(project => {
        if (!project) return project;
        const updatedBRollClips = project.bRollClips.map(clip => {
          if (clip.id === clipId) {
            // Ensure newDuration is not negative or zero
            const safeNewDuration = Math.max(0.1, newDuration);
            return { ...clip, duration: safeNewDuration };
          }
          return clip;
        });
        return { ...project, bRollClips: updatedBRollClips, updatedAt: new Date() };
      });
    },
    addZoomEffect: (effect) => {
      update(project => {
        if (!project) return project;
        return { ...project, zoomEffects: [...project.zoomEffects, effect], updatedAt: new Date() };
      });
    },
    removeZoomEffect: (effectId) => {
      update(project => {
        if (!project) return project;
        return { ...project, zoomEffects: project.zoomEffects.filter(e => e.id !== effectId), updatedAt: new Date() };
      });
    },
    updateZoomEffect: (effectId, updates) => {
      update(project => {
        if (!project) return project;
        const updatedEffects = project.zoomEffects.map(effect => {
          if (effect.id === effectId) {
            return { ...effect, ...updates };
          }
          return effect;
        });
        return { ...project, zoomEffects: updatedEffects, updatedAt: new Date() };
      });
    },
    addSoundEffect: (effect) => {
      update(project => {
        if (!project) return project;
        return { ...project, soundEffects: [...project.soundEffects, effect], updatedAt: new Date() };
      });
    },
    removeSoundEffect: (effectId) => {
      update(project => {
        if (!project) return project;
        return { ...project, soundEffects: project.soundEffects.filter(e => e.id !== effectId), updatedAt: new Date() };
      });
    },
    updateSoundEffect: (effectId, updates) => {
      update(project => {
        if (!project) return project;
        const updatedEffects = project.soundEffects.map(effect => {
          if (effect.id === effectId) {
            return { ...effect, ...updates };
          }
          return effect;
        });
        return { ...project, soundEffects: updatedEffects, updatedAt: new Date() };
      });
    }