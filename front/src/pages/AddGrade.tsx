import { useState, useEffect, FormEvent } from 'react'
import { motion } from 'framer-motion'
import { fetchPrepodStudents, createGrade } from '../api'
import type { StudentOption } from '../types'
import './AddGrade.css'

interface Props {
  userId: number
}

const SUBJECTS = ['Математика', 'Физика', 'Программирование', 'Химия', 'История']
const VALUES = [5, 4, 3, 2]

export default function AddGrade({ userId }: Props) {
  const [students, setStudents] = useState<StudentOption[]>([])
  const [studentId, setStudentId] = useState<number | ''>('')
  const [subject, setSubject] = useState('')
  const [value, setValue] = useState<number>(5)
  const [comment, setComment] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchPrepodStudents(userId)
      .then(setStudents)
      .catch(() => setError('Не удалось загрузить список студентов'))
      .finally(() => setLoading(false))
  }, [userId])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!studentId || !subject) {
      setError('Выберите студента и предмет')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await createGrade(userId, {
        student_id: Number(studentId),
        subject,
        value,
        comment: comment || undefined,
      })
      setSuccess(true)
      setStudentId('')
      setSubject('')
      setValue(5)
      setComment('')
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <motion.div className="addgrade-loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <motion.span className="spinner" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
          ◐
        </motion.span>
        Загрузка...
      </motion.div>
    )
  }

  return (
    <motion.div
      className="addgrade-page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div className="addgrade-card">
        <h2 className="addgrade-title">Выставить оценку</h2>
        {error && (
          <motion.div className="addgrade-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {error}
          </motion.div>
        )}
        {success && (
          <motion.div
            className="addgrade-success"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            ✓ Оценка успешно выставлена. Студент получит уведомление.
          </motion.div>
        )}
        <form onSubmit={handleSubmit} className="addgrade-form">
          <div className="field">
            <label>Студент</label>
            <select
              value={studentId}
              onChange={(e) => setStudentId(e.target.value ? Number(e.target.value) : '')}
              required
            >
              <option value="">Выберите студента</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.group_name})
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Предмет</label>
            <select value={subject} onChange={(e) => setSubject(e.target.value)} required>
              <option value="">Выберите предмет</option>
              {SUBJECTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Оценка</label>
            <div className="value-buttons">
              {VALUES.map((v) => (
                <motion.button
                  key={v}
                  type="button"
                  className={`value-btn ${value === v ? 'active' : ''}`}
                  onClick={() => setValue(v)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {v}
                </motion.button>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Комментарий (необязательно)</label>
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Отличная работа!"
            />
          </div>
          <motion.button
            type="submit"
            className="btn-submit"
            disabled={submitting}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {submitting ? (
              <motion.span className="spinner" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                ◐
              </motion.span>
            ) : (
              'Выставить оценку'
            )}
          </motion.button>
        </form>
      </div>
    </motion.div>
  )
}
