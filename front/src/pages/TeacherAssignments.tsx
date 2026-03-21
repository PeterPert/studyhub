import { useEffect, useState, useCallback, FormEvent } from 'react'
import { motion } from 'framer-motion'
import {
  fetchAssignmentMeta,
  createAssignment,
  fetchTeacherAssignments,
  reviewAssignment,
} from '../api'
import type { AssignmentMeta, AssignmentTeacherItem } from '../types'
import './TeacherAssignments.css'

interface Props {
  userId: number
}

export default function TeacherAssignments({ userId }: Props) {
  const [meta, setMeta] = useState<AssignmentMeta | null>(null)
  const [list, setList] = useState<AssignmentTeacherItem[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [subject, setSubject] = useState('')
  const [groupId, setGroupId] = useState<number | ''>('')
  const [description, setDescription] = useState('')
  const [reviewing, setReviewing] = useState<{ aid: number; sid: number } | null>(null)

  const loadAll = useCallback(() => {
    return Promise.all([fetchAssignmentMeta(userId), fetchTeacherAssignments(userId)]).then(([m, items]) => {
      setMeta(m)
      setList(items)
    })
  }, [userId])

  useEffect(() => {
    setLoading(true)
    setError('')
    loadAll()
      .catch(() => setError('Не удалось загрузить данные'))
      .finally(() => setLoading(false))
  }, [loadAll])

  const handlePublish = async (e: FormEvent) => {
    e.preventDefault()
    if (!subject || !groupId || !description.trim()) {
      setError('Выберите предмет, группу и введите описание')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await createAssignment(userId, {
        subject,
        group_id: Number(groupId),
        description: description.trim(),
      })
      setSuccess(true)
      setDescription('')
      setTimeout(() => setSuccess(false), 3000)
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка публикации')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReview = async (assignmentId: number, studentId: number, accept: boolean) => {
    setReviewing({ aid: assignmentId, sid: studentId })
    setError('')
    try {
      await reviewAssignment(userId, assignmentId, { student_id: studentId, accept })
      await loadAll()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка')
    } finally {
      setReviewing(null)
    }
  }

  if (loading) {
    return (
      <motion.div className="teacher-assignments-loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <motion.span className="spinner" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
          ◐
        </motion.span>
        Загрузка…
      </motion.div>
    )
  }

  return (
    <motion.div
      className="teacher-assignments-page"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <h1 className="assignments-page-title">Задания</h1>

      {meta && (meta.subjects.length === 0 || meta.groups.length === 0) && (
        <p className="teacher-assignments-banner">
          В расписании нет пар с вашим участием (предметы/группы). Добавьте записи расписания через администратора — тогда здесь появятся списки для публикации заданий.
        </p>
      )}

      <div className="teacher-assignments-card">
        <h2 className="teacher-assignments-subtitle">Опубликовать задание</h2>
        {error && (
          <motion.div className="teacher-assignments-error" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            {error}
          </motion.div>
        )}
        {success && (
          <motion.div className="teacher-assignments-success" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            ✓ Задание опубликовано
          </motion.div>
        )}
        <form onSubmit={handlePublish} className="teacher-assignments-form">
          <div className="field">
            <label>Предмет</label>
            <select value={subject} onChange={(e) => setSubject(e.target.value)} required>
              <option value="">Выберите предмет</option>
              {(meta?.subjects ?? []).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Группа</label>
            <select
              value={groupId === '' ? '' : String(groupId)}
              onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : '')}
              required
            >
              <option value="">Выберите группу</option>
              {(meta?.groups ?? []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Описание задания</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Текст задания для студентов"
              rows={5}
              required
            />
          </div>
          <motion.button
            type="submit"
            className="btn-publish"
            disabled={
              submitting ||
              !meta ||
              meta.subjects.length === 0 ||
              meta.groups.length === 0
            }
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {submitting ? (
              <motion.span className="spinner" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
                ◐
              </motion.span>
            ) : (
              'Опубликовать задание'
            )}
          </motion.button>
        </form>
      </div>

      <motion.section
        className="teacher-assignments-list-wrap"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        <h2 className="teacher-assignments-subtitle">Мои задания и статусы студентов</h2>
        {list.length === 0 ? (
          <p className="teacher-assignments-empty">Пока нет опубликованных заданий</p>
        ) : (
          <ul className="teacher-assignments-ul">
            {list.map((a) => (
              <li key={a.id} className="teacher-assignments-item">
                <div className="teacher-assignments-item-head">
                  <span className="teacher-assignments-item-subject">{a.subject}</span>
                  <span className="teacher-assignments-item-meta">
                    {a.group_name} · {new Date(a.created_at).toLocaleString('ru')}
                  </span>
                </div>
                <p className="teacher-assignments-item-desc">{a.description}</p>
                <table className="teacher-assignments-table">
                  <thead>
                    <tr>
                      <th>Студент</th>
                      <th>Стадия</th>
                      <th>Действие</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.students.map((s) => (
                      <tr key={s.student_id}>
                        <td>{s.student_name}</td>
                        <td>
                          {s.teacher_accepted ? (
                            <span className="tag tag-done">Засчитано</span>
                          ) : s.student_status === 'submitted' ? (
                            <span className="tag tag-submitted">Сдано</span>
                          ) : (
                            <span className="tag tag-progress">В процессе</span>
                          )}
                        </td>
                        <td>
                          {!s.teacher_accepted && s.student_status === 'submitted' ? (
                            <div className="review-btns">
                              <button
                                type="button"
                                className="btn-accept"
                                disabled={reviewing?.aid === a.id && reviewing?.sid === s.student_id}
                                onClick={() => handleReview(a.id, s.student_id, true)}
                              >
                                Засчитать
                              </button>
                              <button
                                type="button"
                                className="btn-reject"
                                disabled={reviewing?.aid === a.id && reviewing?.sid === s.student_id}
                                onClick={() => handleReview(a.id, s.student_id, false)}
                              >
                                Не засчитать
                              </button>
                            </div>
                          ) : s.teacher_accepted ? (
                            <span className="review-hint">—</span>
                          ) : (
                            <span className="review-hint">Ждём сдачу</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </li>
            ))}
          </ul>
        )}
      </motion.section>
    </motion.div>
  )
}
