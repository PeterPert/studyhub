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
  grade_id?: number | null
  assignment_id?: number | null
  message: string
  is_read: number
  created_at: string
}

export interface GroupOption {
  id: number
  name: string
}

export interface AssignmentMeta {
  subjects: string[]
  groups: GroupOption[]
}

export interface AssignmentStudentStatusRow {
  student_id: number
  student_name: string
  student_status: 'in_progress' | 'submitted'
  teacher_accepted: boolean
}

export interface AssignmentTeacherItem {
  id: number
  subject: string
  description: string
  group_id: number
  group_name: string
  created_at: string
  students: AssignmentStudentStatusRow[]
}

export interface StudentAssignmentItem {
  id: number
  subject: string
  description: string
  prepod_name: string
  created_at: string
  student_status: 'in_progress' | 'submitted'
}
