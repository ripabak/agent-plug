/** Bundled animated GIF avatar templates (see public/avatars/templates/).
 *
 * Keep in sync with `frontend/scripts/generate-avatar-templates.py`.
 * Picking a template downloads the GIF and uploads it through the normal
 * avatar pipeline (`PUT /api/agents/{id}/avatar`), so it is compressed to
 * WebP and stays animated.
 */
export interface AvatarTemplate {
  id: string
  label: string
  url: string
}

export const AVATAR_TEMPLATES: AvatarTemplate[] = [
  { id: 'rocket', label: 'Rocket', url: '/avatars/templates/rocket.gif' },
  { id: 'robot', label: 'Robot', url: '/avatars/templates/robot.gif' },
  { id: 'heart', label: 'Heart', url: '/avatars/templates/heart.gif' },
  { id: 'chat', label: 'Chat', url: '/avatars/templates/chat.gif' },
  { id: 'brain', label: 'Brain', url: '/avatars/templates/brain.gif' },
  { id: 'wave', label: 'Wave', url: '/avatars/templates/wave.gif' },
  { id: 'star', label: 'Star', url: '/avatars/templates/star.gif' },
  { id: 'owl', label: 'Owl', url: '/avatars/templates/owl.gif' },
  { id: 'bolt', label: 'Bolt', url: '/avatars/templates/bolt.gif' },
  { id: 'sparkles', label: 'Sparkles', url: '/avatars/templates/sparkles.gif' },
]
