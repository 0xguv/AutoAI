import { writable } from 'svelte/store';

// Video player state
function createVideoStore() {
  const { subscribe, set, update } = writable({
    currentTime: 0,
    duration: 0,
    isPlaying: false,
    volume: 1,
    playbackRate: 1
  });

  return {
    subscribe,
    set,
    update,
    setCurrentTime: (time) => update(v => ({ ...v, currentTime: time })),
    setPlaying: (playing) => update(v => ({ ...v, isPlaying: playing })),
    togglePlay: () => update(v => ({ ...v, isPlaying: !v.isPlaying }))
  };
}

export const videoState = createVideoStore();