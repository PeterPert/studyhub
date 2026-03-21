import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { fetchStudentAssignments, patchStudentAssignmentStatus } from '../api'
import type { StudentAssignmentItem } from '../types'
import './StudentAssignments.css'

interface Props {
  userId: number
}

export default function StudentAssignments({ userId }: Props) {
  const [items, setItems] = useState<StudentAssignmentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [updating, setUpdating] = useState<number | null>(null)

  const load = useCallback(() => {
    setError('')
    fetchStudentAssignments(userId)
      .then(setItems)
      .catch(() => setError('Не удалось загрузить задания'))
      .finally(() => setLoading(false))
  }, [userId])

  useEffect(() => {
    load()
  }, [load])

  const setStatus = async (assignmentId: number, student_status: 'in_progress' | 'submitted') => {
    setUpdating(assignmentId)
    setError('')
    try {
      await patchStudentAssignmentStatus(userId, assignmentId, { student_status })
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка сохранения')
    } finally {
      setUpdating(null)
    }
  }

  if (loading) {
    return (
      <motion.div className="assignments-loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <motion.span className="spinner" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
          ◐
        </motion.span>
        Загрузка заданий…
      </motion.div>
    )
  }

  return (
    <motion.div
      className="student-assignments-page"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <h1 className="assignments-page-title">Задания</h1>
      <p className="assignments-page-hint">Выберите свой этап: «в процессе» или «сдано». После проверки преподавателя засчитанная работа исчезнет из списка.</p>
      {error && <div className="assignments-error">{error}</div>}

      {items.length === 0 ? (
        <div className="assignments-empty">Нет активных заданий</div>
      ) : (
        <ul className="assignments-feed">
          {items.map((a) => (
            <li key={a.id} className="assignment-card">
              <div className="assignment-card-header">
                <span className="assignment-subject">{a.subject}</span>
                <span className="assignment-date">{new Date(a.created_at).toLocaleDateString('ru')}</span>
              </div>
              <p className="assignment-prepod">{a.prepod_name}</p>
              <p className="assignment-desc">{a.description}</p>
              <div className="assignment-stages">
                <span className="assignment-stages-label">Стадия:</span>
                <div className="assignment-stage-btns">
                  <button
                    type="button"
                    className={`stage-btn ${a.student_status === 'in_progress' ? 'active' : ''}`}
                    disabled={updating === a.id}
                    onClick={() => setStatus(a.id, 'in_progress')}
                  >
                    В процессе
                  </button>
                  <button
                    type="button"
                    className={`stage-btn ${a.student_status === 'submitted' ? 'active' : ''}`}
                    disabled={updating === a.id}
                    onClick={() => setStatus(a.id, 'submitted')}
                  >
                    Сдано
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  )
}
