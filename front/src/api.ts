import type {
  User,
  ScheduleItem,
  Grade,
  StudentOption,
  Notification,
  AssignmentMeta,
  AssignmentTeacherItem,
  StudentAssignmentItem,
} from './types'

const API = '/api'

function headers(userId: number): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-User-Id': String(userId),
  }
}

export async function login(login: string, password: string): Promise<User> {
  const res = await fetch(`${API}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login, password }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || 'Неверный логин или пароль')
  }
  const user = await res.json()
  if (user.role !== 'student' && user.role !== 'prepod') {
    throw new Error('Вход только для студентов и преподавателей')
  }
  return user
}

export async function fetchSchedule(userId: number, role: 'student' | 'prepod', dayOfWeek: number): Promise<ScheduleItem[]> {
  const path = role === 'prepod' ? `schedule/teacher/${userId}` : `schedule/student/${userId}`
  const res = await fetch(`${API}/${path}?day_of_week=${dayOfWeek}`)
  if (!res.ok) throw new Error('Ошибка загрузки расписания')
  return res.json()
}

// --- Оценки и уведомления ---

export async function fetchPrepodStudents(userId: number): Promise<StudentOption[]> {
  const res = await fetch(`${API}/prepod/${userId}/students`, { headers: headers(userId) })
  if (!res.ok) throw new Error('Ошибка загрузки списка студентов')
  return res.json()
}

export async function createGrade(userId: number, data: { student_id: number; subject: string; value: number; comment?: string }): Promise<Grade> {
  const res = await fetch(`${API}/prepod/grades`, {
    method: 'POST',
    headers: headers(userId),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Ошибка при выставлении оценки')
  }
  return res.json()
}

export async function fetchStudentGroupName(userId: number): Promise<{ group_name: string }> {
  const res = await fetch(`${API}/student/${userId}/group`, { headers: headers(userId) })
  if (!res.ok) throw new Error('Не удалось загрузить группу')
  return res.json()
}

export async function fetchStudentGrades(userId: number): Promise<Grade[]> {
  const res = await fetch(`${API}/student/${userId}/grades`, { headers: headers(userId) })
  if (!res.ok) throw new Error('Ошибка загрузки оценок')
  return res.json()
}

export async function fetchNotifications(userId: number, unreadOnly = false): Promise<Notification[]> {
  const q = unreadOnly ? '?unread_only=true' : ''
  const res = await fetch(`${API}/student/${userId}/notifications${q}`, { headers: headers(userId) })
  if (!res.ok) throw new Error('Ошибка загрузки уведомлений')
  return res.json()
}

export async function fetchUnreadCount(userId: number): Promise<number> {
  const res = await fetch(`${API}/student/${userId}/notifications/unread-count`, { headers: headers(userId) })
  if (!res.ok) return 0
  const data = await res.json()
  return data.count ?? 0
}

export async function markNotificationRead(userId: number, notifId: number): Promise<void> {
  await fetch(`${API}/student/${userId}/notifications/${notifId}/read`, {
    method: 'PATCH',
    headers: headers(userId),
  })
}

export async function markAllNotificationsRead(userId: number): Promise<void> {
  await fetch(`${API}/student/${userId}/notifications/read-all`, {
    method: 'PATCH',
    headers: headers(userId),
  })
}

// --- Задания ---

export async function fetchAssignmentMeta(userId: number): Promise<AssignmentMeta> {
  const res = await fetch(`${API}/prepod/${userId}/assignment-meta`, { headers: headers(userId) })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Ошибка загрузки предметов и групп')
  }
  return res.json()
}

export async function createAssignment(
  userId: number,
  data: { subject: string; description: string; group_id: number }
): Promise<{ id: number; ok: boolean }> {
  const res = await fetch(`${API}/prepod/assignments`, {
    method: 'POST',
    headers: headers(userId),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Не удалось опубликовать задание')
  }
  return res.json()
}

export async function fetchTeacherAssignments(userId: number): Promise<AssignmentTeacherItem[]> {
  const res = await fetch(`${API}/prepod/${userId}/assignments`, { headers: headers(userId) })
  if (!res.ok) throw new Error('Ошибка загрузки заданий')
  return res.json()
}

export async function fetchStudentAssignments(userId: number): Promise<StudentAssignmentItem[]> {
  const res = await fetch(`${API}/student/${userId}/assignments`, { headers: headers(userId) })
  if (!res.ok) throw new Error('Ошибка загрузки заданий')
  return res.json()
}

export async function patchStudentAssignmentStatus(
  userId: number,
  assignmentId: number,
  data: { student_status: 'in_progress' | 'submitted' }
): Promise<void> {
  const res = await fetch(`${API}/student/${userId}/assignments/${assignmentId}/status`, {
    method: 'PATCH',
    headers: headers(userId),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Не удалось сохранить статус')
  }
}

export async function reviewAssignment(
  userId: number,
  assignmentId: number,
  data: { student_id: number; accept: boolean }
): Promise<void> {
  const res = await fetch(`${API}/prepod/assignments/${assignmentId}/review`, {
    method: 'PATCH',
    headers: headers(userId),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Ошибка проверки')
  }
}
