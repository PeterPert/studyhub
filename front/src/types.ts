export interface User {
  id: number
  role: 'student' | 'prepod'
  name: string
}

export interface ScheduleItem {
  id: number
  date: string
  time: string
  subject: string
  classroom: string
  group_id?: number
  prepod_id?: number
}

export interface Grade {
  id: number
  student_id: number
  prepod_id: number
  subject: string
  value: number
  comment: string | null
  created_at: string
  prepod_name?: string
}

export interface StudentOption {
  id: number
  name: string
  group_name: string
}

export interface Notification {
  id: number
  grade_id: number
  message: string
  is_read: number
  created_at: string
}
