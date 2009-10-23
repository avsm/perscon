module TimeDB :
  sig
    val with_db :
      float -> (Schema.Entry.Orm._cache Schema.Entry.Orm.OS.state -> 'a) -> 'a
  end

module SingleDB :
  sig
    val with_db :
      (Schema.Entry.Orm._cache Schema.Entry.Orm.OS.state -> 'a) -> 'a
  end
