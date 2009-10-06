module TimeDB :
  sig
    val with_db :
      float -> (Schema.Entry.Orm._cache Schema.Entry.OS.state -> 'a) -> 'a
  end

