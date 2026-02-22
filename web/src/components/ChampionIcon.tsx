import { useState } from 'react'
import Avatar from '@mui/material/Avatar'
import { getDDragonKey } from '../utils/championMapping'

const DDRAGON_VERSION = '15.4.1'
const BASE = `https://ddragon.leagueoflegends.com/cdn/${DDRAGON_VERSION}/img/champion/`

interface Props {
  name: string
}

export function ChampionIcon({ name }: Props) {
  const [error, setError] = useState(false)
  const key = getDDragonKey(name)

  return (
    <Avatar
      src={error ? undefined : `${BASE}${key}.png`}
      alt={name}
      imgProps={{ loading: 'lazy', onError: () => setError(true) }}
      sx={{ width: 32, height: 32, fontSize: 12 }}
    >
      {name[0]}
    </Avatar>
  )
}
