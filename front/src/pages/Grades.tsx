import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchStudentGrades } from '../api'
import type { Grade } from '../types'
import './Grades.css'

interface Props {
  userId: number
}

export default function Grades({ userId }: Props) {
  const [grades, setGrades] = useState<Grade[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    fetchStudentGrades(userId)
      .then(setGrades)
      .catch(() => setError('Не удалось загрузить оценки'))
      .finally(() => setLoading(false))
  }, [userId])

  const avg = grades.length ? (grades.reduce((s, g) => s + g.value, 0) / grades.length).toFixed(1) : null

  if (loading) {
    return (
      <motion.div className="grades-loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <motion.span
          className="spinner"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        >
          ◐
        </motion.span>
        Загрузка...
      </motion.div>
    )
  }

  if (error) {
    return <motion.p className="grades-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>{error}</motion.p>
  }

  return (
    <motion.div
      className="grades-page"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {avg && (
        <motion.div
          className="grades-summary"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          <span className="summary-label">Средний балл</span>
          <span className="summary-value">{avg}</span>
        </motion.div>
      )}
      <div className="grades-card">
        <h2 className="grades-title">Мои оценки</h2>
        {grades.length === 0 ? (
          <motion.p className="grades-empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            Пока нет оценок
          </motion.p>
        ) : (
          <div className="grades-list">
            <AnimatePresence mode="popLayout">
              {grades.map((g, i) => (
                <motion.div
                  key={g.id}
                  className="grade-item"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <div className="grade-main">
                    <span className="grade-subject">{g.subject}</span>
                    <motion.span
                      className={`grade-value grade-${g.value}`}
                      whileHover={{ scale: 1.1 }}
                      transition={{ type: 'spring', stiffness: 400 }}
                    >
                      {g.value}
                    </motion.span>
                  </div>
                  <div className="grade-meta">
                    {g.prepod_name && <span>{g.prepod_name}</span>}
                    <span>{new Date(g.created_at).toLocaleDateString('ru')}</span>
                  </div>
                  {g.comment && <p className="grade-comment">{g.comment}</p>}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  )
}
