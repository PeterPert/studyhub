import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { login } from '../api'
import './Login.css'

export default function Login() {
  const navigate = useNavigate()
  const [loginVal, setLoginVal] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(loginVal, password)
      sessionStorage.setItem('user', JSON.stringify(user))
      navigate('/schedule')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-bg">
        <motion.div
          className="blob blob-1"
          animate={{ x: [0, 30, 0], y: [0, -20, 0], scale: [1, 1.05, 1] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="blob blob-2"
          animate={{ x: [0, -20, 0], y: [0, 30, 0], scale: [1, 1.1, 1] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="blob blob-3"
          animate={{ x: [0, 15, 0], y: [0, 15, 0] }}
          transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <motion.div
        className="login-card"
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.div
          className="login-header"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <img className="logo-image" src="/bmstu-logo.svg" alt="Логотип МГТУ им. Н.Э. Баумана" />
          <motion.span
            className="logo"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.3, type: 'spring', stiffness: 200 }}
          >
            StudyHub
          </motion.span>
          <p className="subtitle">Войдите, чтобы увидеть расписание</p>
        </motion.div>

        <form onSubmit={handleSubmit} className="login-form">
          <motion.div
            className="field"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.35 }}
          >
            <label htmlFor="login">Логин</label>
            <input
              id="login"
              type="text"
              value={loginVal}
              onChange={(e) => setLoginVal(e.target.value)}
              placeholder="Введите логин"
              required
              autoComplete="username"
              autoFocus
              disabled={loading}
            />
          </motion.div>
          <motion.div
            className="field"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <label htmlFor="password">Пароль</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Введите пароль"
              required
              autoComplete="current-password"
              disabled={loading}
            />
          </motion.div>

          {error && (
            <motion.div
              className="error-msg"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              {error}
            </motion.div>
          )}

          <motion.button
            type="submit"
            className="btn-login"
            disabled={loading}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            whileHover={{ scale: 1.02, boxShadow: '0 0 30px rgba(99, 102, 241, 0.4)' }}
            whileTap={{ scale: 0.98 }}
          >
            {loading ? (
              <motion.span
                className="spinner"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              >
                ◐
              </motion.span>
            ) : (
              'Войти'
            )}
          </motion.button>
        </form>
      </motion.div>

      <motion.p
        className="hint"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
      >
        Студент: student1 / 123 · Преподаватель: prepod1 / 123
      </motion.p>
    </div>
  )
}
